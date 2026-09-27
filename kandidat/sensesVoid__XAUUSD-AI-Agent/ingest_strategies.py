from pathlib import Path
from strategy_rag import StrategyRAG

def main():
    rag = StrategyRAG()
    strategy_dir = Path("strategies")

    if not strategy_dir.exists():
        raise FileNotFoundError(
            "strategies/ folder not found — create it and add your .md files first"
        )

    md_files = list(strategy_dir.glob("*.md"))
    if not md_files:
        print("No .md files found in strategies/ — nothing to ingest")
        return

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        rag.ingest_strategy_doc(
            doc_id=md_file.stem,
            text=text,
            metadata={"instrument": "XAUUSD", "source_file": md_file.name},
        )
        print(f"Ingested: {md_file.name}")

    print(f"Done. {len(md_files)} strategy doc(s) in the vector store.")

if __name__ == "__main__":
    main()