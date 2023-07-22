# VecTrekker

## Overview

VecTrekker is a simple utility to easily walk through a directory of files, and
sync them to a vector database (for example, [Pinecone]). You can use it (for
example) to index your notes for use with an LLM chain.

## Quick-start guide

```bash
pip install vectrekker
vectrekker --dry-run
```

## Scheduling VecTrekker

It's suggested that you setup a crontab for VecTrekker to periodically scan
your directories again, and update any files that are out of date. An example
crontab scanning every two hours is

```cron
0 */2 * * * ~/.vectrekker/.venv/bin/vectrekker
```

## Vector database support

These are the currently supported vector databases.

| Database   | Support |
| ---------- | ------- |
| [Pinecone] | ✅       |

[Pinecone]: https://www.pinecone.io/
