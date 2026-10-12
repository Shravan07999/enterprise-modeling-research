# 4EM Literature Ingestion Guide

The HyDE vector database is populated with excerpts from core 4EM literature to ground retrieval during model generation.

Because these textbooks are copyrighted, they cannot be bundled directly in this repository. To reproduce the exact knowledge base used during evaluation, acquire the source publications listed below and run the local ingestion script.

## Reference Publications

1. **Enterprise Modeling: Tackling Business Challenges with the 4EM Approach**
   - Authors: Kurt Sandkuhl, Janis Stirna, Anne Persson, Matthias Wißotzki
   - Publisher: Springer (2014)
   - DOI: [10.1007/978-3-662-43786-5](https://doi.org/10.1007/978-3-662-43786-5)
   - Expected filename: `Book1-EM Sandkuhl 4EM.pdf`

2. **4EM Perspectives and Methods**
   - Authors: Janis Stirna, Anne Persson
   - Reference on 4EM modeling sub-models (Goals, Business Processes, Concepts, Actors & Resources, Technical Components)
   - Expected filename: `Book 2-4EM Perspectives and methods.pdf`

3. **Janis Stirna Doctoral Thesis / Compendium**
   - Author: Janis Stirna
   - Participative enterprise modeling and patterns
   - Expected filename: `Book 3-Janis Stirna.pdf`

## Ingestion Steps

1. Place the PDF files into:
   ```
   HyDE/backend/data/
   ```

2. Configure your OpenAI API key:
   ```bash
   cp HyDE/.env.example HyDE/.env
   ```

3. Run the ingestion pipeline:
   ```bash
   cd HyDE/backend/ingestion_service
   pip install -r requirements.txt
   python ingest.py
   ```
   The script chunks the text, creates embeddings with `text-embedding-3-small`, and stores them locally in `HyDE/backend/chroma_db/`.

## Testing Without External Books

A synthetic metamodel reference is provided at:
```
HyDE/backend/data/sample_4em_reference.md
```
This file summarizes core 4EM concepts and relationships so the ingestion and query pipeline can be validated without needing the external PDFs.
