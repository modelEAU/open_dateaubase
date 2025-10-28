# Database Documentation

Welcome to the automatically generated database documentation.

## Overview

This documentation is generated from the database metadata table, which describes all tables, columns, relationships, and controlled vocabularies in the database system.

## Navigation

- **[Database Schema](reference/schema.md)** - Overview of all tables and value sets
- **[Tables](reference/tables.md)** - Detailed table documentation with columns and relationships
- **[Value Sets](reference/valuesets.md)** - Controlled vocabularies and enumerations

## About

This documentation system uses:
- **MkDocs** with Material theme for presentation
- **mkdocs-gen-files** plugin for dynamic documentation generation
- A Python hook that parses the Parts metadata table and generates markdown files

The documentation automatically updates whenever the metadata table changes and MkDocs is rebuilt.