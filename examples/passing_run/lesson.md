# Introduction to RAG (Retrieval-Augmented Generation)

## What is RAG

Imagine you are a student in an exam. You do not remember everything. So, you open your textbook. You find the right page. Then, you write the answer.

RAG works the same way. RAG stands for Retrieval-Augmented Generation. It is a method for AI. Before an AI answers a question, it looks for help. It searches a set of documents. It finds the most useful text. Then, it uses that text to answer.

We use a Large Language Model (LLM) for this. An LLM is a type of AI. It is trained on huge amounts of text. It can write, summarize, and chat. But it only knows what it learned during training. It does not know new or private information. RAG fixes this. It gives the AI specific "notes" for each question.

## Why it matters

LLMs have a problem. They sometimes "hallucinate." This word means the AI makes up facts. It writes fluent, smooth text. But the text is false. This is dangerous. If a doctor asks about a drug, a wrong answer is bad.

RAG helps reduce this. It grounds the answer in real documents. The AI reads a rule book or a help article. It answers based on that text. This makes answers more accurate. It also keeps information up to date. If a fee changes, you update the document. You do not need to retrain the AI. This saves money and time.

Consider a real-world use case. A college wants a chatbot for students. Students ask, "What is the exam fee?" The chatbot searches the college rule book. It finds the exact fee. It answers correctly. Without RAG, the AI might guess. Or it might give an old fee from its training data. RAG ensures the answer comes from the current rule book.

## How it works

RAG has two main phases. First is storage. Second is answering.

In the storage phase, we prepare documents. We take PDFs, web pages, or notes. We split them into small pieces. This is called **chunking**. A chunk is a small part of text. It might be one paragraph. We do this so the AI can find specific details.

Next, we process each chunk. We use an embedding model. This model turns text into numbers. These numbers are called **embeddings**. An embedding is a list of numbers. It captures the meaning of the text. Words with similar meaning get similar numbers.

We store these numbers in a **vector database**. A vector is just a list of numbers. A vector database is special software. It stores these lists. It can find similar lists very fast.

In the answering phase, a user asks a question. The system turns the question into an embedding. Then, it runs a **similarity search**. This search looks for chunks with similar meaning. It finds the top few chunks. This step is called **retrieving**. Retrieving means finding the right text pieces.

Now, the system **augments** the prompt. Augmentation means adding extra information. A **prompt** is the instruction you give to the AI. The system adds the retrieved chunks to the question. It creates a new, longer prompt.

Finally, the LLM **generates** the answer. Generation means creating new text. It reads the new prompt. It writes a response. It uses the provided text as the main source of facts.

## Worked example

Let us trace a specific example. A student asks an AI chatbot: "What are the fees for the Class 10 board exam in UP?"

First, the **Retrieve** step happens. The system searches a stored PDF of "UP Board Fee Rules." It ignores pages about theory exams. It finds a small text chunk. This chunk says: "Practical Exam Fee: ₹500."

Second, the **Augment** step happens. The system creates a new prompt for the AI. It combines the rule with the question. The new prompt says: "Here is the rule: 'Practical Exam Fee: ₹500'. Now answer: What are the fees for the Class 10 board exam?"

Third, the **Generate** step happens. The AI reads this new prompt. It sees the specific rule. It writes the final reply. The reply is: "According to the UP Board rules, the practical exam fee is ₹500."

This process is fast. It happens in milliseconds. The user just sees a quick, correct answer.

## Limits, and RAG compared with fine-tuning

RAG has limits. First, if the retrieval is bad, the answer is bad. If the system finds the wrong chunk, the AI will give a wrong answer. The AI trusts the text it is given.

Second, source quality matters. If the documents are wrong or old, the answer is wrong. You must keep your documents updated.

Third, there is a **context window**. An LLM can only read a limited amount of text at once. This limit is measured in **tokens**. A token is a small unit of text. It is often a piece of a word. If you give too many chunks, the AI cannot read them all. So, you must pick the most relevant chunks.

Fourth, the AI can still make mistakes. It might misread the text. It might still hallucinate, though less often.

Now, let us compare RAG with **fine-tuning**. Fine-tuning means training the model more. You give it your own examples. This changes the model's weights. Weights are the internal settings of the model. They are adjusted during training to learn patterns.

RAG does not change the model. The model stays the same. RAG only gives it extra text at answer time.

Use RAG for facts that change often. For example, prices, dates, or policies. Use fine-tuning for style or behavior. For example, making the AI sound friendly. RAG is cheaper for updating knowledge. You just update files. Fine-tuning requires new training. This is slower and costlier.

## Key words

- **Chunking**: Splitting long documents into smaller pieces of text so they are easier to search and use.
- **Embeddings**: Lists of numbers that represent the meaning of text, allowing computers to compare meanings.
- **Vector Database**: Software that stores embeddings and allows for fast similarity searches.
- **Similarity Search**: A process to find text chunks whose meaning is closest to a user's question.
- **Prompt**: The input instruction given to an AI, which may include the question and retrieved context.
- **Retrieval**: The step of finding the most relevant pieces of text from a collection of documents.
- **Augmentation**: Adding the retrieved text to the prompt together with the user's question.
- **Generation**: The step where the LLM writes the final answer using the provided context.
- **LLM**: A Large Language Model, an AI system trained on large amounts of text to generate language.
- **Hallucination**: When an AI produces fluent text that is factually incorrect or made up.
- **Context Window**: The maximum amount of text an LLM can process at one time.
- **Fine-tuning**: Further training an existing AI model on specific data to change its behavior.
- **Token**: A small unit of text used to measure the length of input or output.

## Recap

Let us summarize the flow. First, we have documents. We split them into chunks. We turn chunks into embeddings. We store these in a vector database.

Then, a user asks a question. The question becomes an embedding. The system runs a similarity search. It finds the best matching chunks. These chunks are added to the prompt. This is augmentation.

Finally, the LLM generates the answer. It uses the retrieved text as its source. This makes the answer grounded in real data. The model itself is not changed. It just gets better notes for each question.

## Check your understanding

1. True or False: RAG changes the internal weights of the LLM to learn new facts.
   **Answer:** False. RAG does not change the model. It only adds text to the prompt.

2. What is the main purpose of chunking documents in RAG?
   **Answer:** To split long texts into small pieces so the AI can find specific details easily.

3. A company wants an AI to answer employee questions about the latest leave policy. The policy changes every quarter. Should they use RAG or fine-tuning?
   **Answer:** They should use RAG. It is easier to update the policy document than to retrain the model.

4. If the similarity search finds the wrong document chunk, what happens to the final answer?
   **Answer:** The final answer will likely be wrong or incomplete because the AI relies on that retrieved text.
