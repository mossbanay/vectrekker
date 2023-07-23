# VecTrekker

## Overview

VecTrekker is a simple utility to easily walk through a directory of files, and
sync them to a vector database (for example, [Pinecone]). You can use it (for
example) to index your notes for use with an LLM chain.

The current tokenizer is `cl100k_base` and the current embedding model used is
`text-embedding-ada-002` from OpenAI.

## Quick-start guide

```bash
pip install vectrekker
vectrekker --dry-run
```

You can adjust the configuration in `~/.vectrekker/config.toml` to add your
credentials for Pinecone, as well as OpenAI.

## Scheduling VecTrekker

It's suggested that you setup a crontab for VecTrekker to periodically scan
your directories again, and update any files that are out of date. An example
crontab scanning every two hours is

```cron
0 * * * * date >> ~/.vectrekker/vectrekker.log && ~/dev/vectrekker/.venv/bin/vectrekker 2>&1 >> ~/.vectrekker/vectrekker.log
```

## Vector database support

These are the currently supported vector databases.

| Database   | Support |
| ---------- | ------- |
| [Pinecone] | ✅       |

[Pinecone]: https://www.pinecone.io/
