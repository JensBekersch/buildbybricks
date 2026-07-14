# Agentic RAG Basics

Agentic RAG verbindet Retrieval Augmented Generation mit einem kontrollierten Agentenablauf. Das System ruft nicht nur passende Textstellen ab, sondern entscheidet in kleinen Schritten, ob weitere Suche, Quellenvergleich oder eine Antwort mit Zitaten sinnvoll ist.

In dieser Demo-Instanz liegt Wissen unter `data/agentic-rag-demo/knowledge/`. Jede App-Instanz kann eigene Collections, eigene Antwortregeln und eigene Evaluationsfaelle besitzen.

Die erste Ingestion soll Textdateien lesen, einfache Chunks erzeugen und Metadaten wie Collection, Dateipfad und Chunk-Index erhalten.
