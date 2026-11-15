# RAG reference sheet (ground truth for the accuracy judge)

This sheet is the single source of truth for the lesson. The accuracy judge fails a lesson
only if a claim in the lesson **contradicts** this sheet. Simplifications are fine; wrong
statements are not.

## Definition
- RAG stands for **Retrieval-Augmented Generation**.
- It was introduced in a 2020 research paper by Patrick Lewis and colleagues at Facebook AI Research.
- RAG is a technique where, before a large language model (LLM) answers, the system first
  **retrieves** relevant text from an outside collection of documents, **augments** (adds to)
  the prompt with that text, and then the LLM **generates** an answer using it.
- The three steps are: **Retrieve -> Augment -> Generate**.

## Why it matters
- An LLM only knows what was in its training data, up to a cut-off date. It does not know
  recent events or private documents (for example, a company's internal policies).
- LLMs can **hallucinate**: produce fluent text that is false or made up.
- RAG grounds answers in chosen source documents, so answers can be more accurate,
  up to date and specific to an organisation.
- RAG can show **sources** (which document a fact came from), so people can check answers.
- Knowledge is updated by **updating the documents**; no model training is needed.
- RAG **reduces** hallucination but does **not eliminate** it.

## How it works
RAG has two phases.

### Phase 1: Indexing (done ahead of time, and again when documents change)
1. **Collect documents** (PDFs, web pages, notes, help articles). This collection is often
   called the **knowledge base**.
2. **Chunking**: split documents into smaller pieces called **chunks** (for example, a
   paragraph or a few hundred words). Chunks are small enough to search precisely and to fit
   into the prompt. Chunks often overlap a little so meaning is not cut in half.
3. **Embedding**: an **embedding model** turns each chunk into an **embedding**, a list of
   numbers (a **vector**) that represents the meaning of the text. Texts with similar meaning
   get vectors that are close together.
4. **Store** the vectors (with the original chunk text) in a **vector database** (or vector
   index), which can quickly find vectors that are close to a given vector.

### Phase 2: Query time (every time a user asks a question)
1. The user's question is turned into an embedding using the **same** embedding model.
2. **Retrieve**: the **retriever** runs a **similarity search** in the vector database to find
   the chunks whose vectors are closest to the question's vector (often the top 3 to 5 chunks,
   called "top-k"). Closeness is commonly measured with cosine similarity. This finds text with
   similar **meaning**, not only matching keywords.
3. **Augment**: the retrieved chunks are inserted into the **prompt** together with the
   user's question and instructions (for example, "Answer using only the context below").
4. **Generate**: the LLM reads the augmented prompt and writes the answer, using the
   retrieved chunks as its main source of facts.

## What RAG is NOT (common misconceptions)
- RAG does **not** retrain, fine-tune or change the LLM's weights. The model stays exactly the
  same; it is only given extra text in the prompt at answer time.
- RAG does **not** store documents "inside" the model. Documents live in an outside store.
- RAG does **not** guarantee correct answers.
- RAG is **not** the same as a normal keyword search engine: it combines search with an LLM
  that writes an answer. (Some systems combine keyword and vector search, called "hybrid search".)
- The LLM does **not** read the whole knowledge base for every question, only the
  retrieved chunks.

## Limits
- **Retrieval quality limits answer quality**: if the wrong chunks are retrieved, the answer
  will be wrong or incomplete.
- **Source quality**: wrong or outdated documents lead to wrong answers.
- **Chunking choices matter**: chunks that are too small lose context; too large add noise.
- **Context window**: an LLM can only read a limited amount of text (measured in tokens) at
  once, so only a limited number of chunks fit in the prompt.
- The LLM can still **hallucinate** or misread the retrieved text.
- Extra **cost and latency**: each question needs an embedding, a search and an LLM call.

## RAG vs fine-tuning
- **Fine-tuning** means further training an existing model on your own examples. It
  **changes the model's weights**.
- Fine-tuning is good for teaching a **style, format or behaviour/task**.
- RAG is better for giving a model **facts or knowledge that change often** or are private,
  and for showing sources.
- Updating knowledge with RAG means updating documents (cheap, fast). With fine-tuning it
  means training again (slower, more costly).
- They can be **combined**.

## Real use cases
- A customer support chatbot that answers from a company's help articles.
- An HR assistant that answers employee questions from the company's policy documents.
- A college help desk bot that answers from the rule book, fee list and timetable.
- A legal or medical assistant that searches large document collections and cites sources.
