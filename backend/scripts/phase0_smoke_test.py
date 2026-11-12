"""DocuIntel AI - Phase 0 smoke test (no database server needed)."""
import io
import os
import platform
import secrets
import sys
import time
import traceback
import zipfile
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

SHARED = {}
RESULTS = []


def ver(dist):
    try:
        return version(dist)
    except PackageNotFoundError:
        return "NOT INSTALLED"


def run(name, dists, fn):
    start = time.perf_counter()
    ok, detail = True, ""
    try:
        detail = fn() or ""
    except Exception:
        ok = False
        tb = traceback.format_exc().strip().splitlines()
        detail = "\n      " + "\n      ".join(tb[-6:])
    versions = ", ".join(f"{d} {ver(d)}" for d in dists)
    elapsed = time.perf_counter() - start
    print(f"[{'PASS' if ok else 'FAIL'}] {name:<18} {versions} | {detail} ({elapsed:.1f}s)")
    RESULTS.append(ok)


def make_pdf(text):
    stream = f"BT /F1 14 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def t_fastapi():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import uvicorn  # noqa: F401

    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    r = TestClient(app).get("/ping")
    assert r.status_code == 200 and r.json() == {"ok": True}
    return "GET /ping ok"


def t_psycopg():
    import psycopg
    from psycopg import pq

    return f"libpq={pq.version()} impl={getattr(pq, '__impl__', '?')}"


def t_sqlalchemy():
    from sqlalchemy import String, create_engine, select
    from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"
        id: Mapped[int] = mapped_column(primary_key=True)
        email: Mapped[str] = mapped_column(String(255), unique=True)

    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(User(email="a@b.c"))
        s.commit()
        assert s.scalars(select(User)).one().email == "a@b.c"
    pg = create_engine("postgresql+psycopg://u:p@localhost:5432/db")  # no connection made
    assert pg.dialect.driver == "psycopg"
    return "ORM roundtrip ok; postgresql+psycopg dialect loads"


def t_alembic():
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    eng = sa.create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        op = Operations(MigrationContext.configure(conn))
        op.create_table("t", sa.Column("id", sa.Integer, primary_key=True), sa.Column("n", sa.String(20)))
        assert "t" in sa.inspect(conn).get_table_names()
    return "create_table operation ok"


def t_argon2():
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    ph = PasswordHasher()
    h = ph.hash("correct horse battery staple")
    assert h.startswith("$argon2id$")
    assert ph.verify(h, "correct horse battery staple")
    try:
        ph.verify(h, "wrong password")
    except VerifyMismatchError:
        return "argon2id hash/verify/reject ok"
    raise AssertionError("wrong password was accepted")


def t_jwt():
    import jwt

    key = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    tok = jwt.encode({"sub": "u1", "exp": now + timedelta(minutes=15)}, key, algorithm="HS256")
    assert jwt.decode(tok, key, algorithms=["HS256"])["sub"] == "u1"
    expired = jwt.encode({"sub": "u1", "exp": now - timedelta(seconds=5)}, key, algorithm="HS256")
    for bad_token, bad_key, exc in [(expired, key, jwt.ExpiredSignatureError),
                                    (tok, key + "x", jwt.InvalidSignatureError)]:
        try:
            jwt.decode(bad_token, bad_key, algorithms=["HS256"])
        except exc:
            continue
        raise AssertionError(f"{exc.__name__} not raised")
    return "encode/decode/expiry/bad-signature ok"


def t_pypdf():
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(make_pdf("DocuIntel smoke test page one")))
    assert len(reader.pages) == 1
    assert "DocuIntel smoke test" in reader.pages[0].extract_text()
    return "1 page parsed, text extracted"


def t_docx():
    from docx import Document

    d = Document()
    d.add_heading("Section One", level=1)
    d.add_paragraph("DocuIntel smoke test paragraph.")
    tbl = d.add_table(rows=1, cols=2)
    tbl.rows[0].cells[0].text, tbl.rows[0].cells[1].text = "A", "B"
    buf = io.BytesIO()
    d.save(buf)
    assert "word/document.xml" in zipfile.ZipFile(buf).namelist()
    buf.seek(0)
    d2 = Document(buf)
    assert d2.paragraphs[0].style.name == "Heading 1" and d2.paragraphs[0].text == "Section One"
    assert "smoke test" in d2.paragraphs[1].text
    assert d2.tables[0].rows[0].cells[1].text == "B"
    return "heading, paragraph, table parsed"


def t_torch():
    import torch

    y = torch.rand(64, 64) @ torch.rand(64, 64)
    assert tuple(y.shape) == (64, 64)
    return f"cuda_available={torch.cuda.is_available()} threads={torch.get_num_threads()}"


def t_st():
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    emb = model.encode(
        ["The contract ends on 31 December.",
         "When does the agreement terminate?",
         "Bananas are rich in potassium."],
        normalize_embeddings=True,
    )
    assert emb.shape == (3, 384)
    related, unrelated = float(emb[0] @ emb[1]), float(emb[0] @ emb[2])
    assert related > unrelated
    SHARED["emb"] = emb
    return f"dim=384 max_seq_length={model.max_seq_length} related={related:.2f} unrelated={unrelated:.2f}"


def t_chroma():
    import chromadb
    import numpy as np

    emb, source = SHARED.get("emb"), "real embeddings"
    if emb is None:
        emb, source = np.random.default_rng(0).random((3, 384)), "RANDOM vectors (embedding test failed)"
    col = chromadb.EphemeralClient().get_or_create_collection("smoke")
    col.add(
        ids=["c1", "c2", "c3"],
        embeddings=emb.tolist(),
        metadatas=[{"user_id": "u1", "document_id": "d1"},
                   {"user_id": "u1", "document_id": "d1"},
                   {"user_id": "u2", "document_id": "d2"}],
    )
    res = col.query(query_embeddings=[emb[1].tolist()], n_results=2, where={"user_id": "u1"})
    ids = res["ids"][0]
    assert ids[0] == "c2" and set(ids) == {"c1", "c2"}, ids
    col.delete(where={"document_id": "d1"})
    assert col.count() == 1
    return f"add/query/filter/delete ok ({source})"


if __name__ == "__main__":
    print(f"Python {sys.version.split()[0]} | {platform.platform()}")
    print(f"Interpreter: {sys.executable}\n")
    run("fastapi", ["fastapi", "pydantic", "uvicorn", "httpx"], t_fastapi)
    run("psycopg", ["psycopg", "psycopg-binary"], t_psycopg)
    run("sqlalchemy", ["sqlalchemy"], t_sqlalchemy)
    run("alembic", ["alembic"], t_alembic)
    run("argon2", ["argon2-cffi"], t_argon2)
    run("pyjwt", ["pyjwt"], t_jwt)
    run("pypdf", ["pypdf"], t_pypdf)
    run("python-docx", ["python-docx"], t_docx)
    run("torch (cpu)", ["torch"], t_torch)
    run("sentence-trans.", ["sentence-transformers", "transformers"], t_st)
    run("chromadb", ["chromadb", "numpy"], t_chroma)
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed")
    sys.exit(0 if all(RESULTS) else 1)
    