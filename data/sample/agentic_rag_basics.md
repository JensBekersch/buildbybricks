# Agentic RAG Basics

Agentic RAG verbindet Retrieval Augmented Generation mit einem kontrollierten Agentenablauf. Das System ruft nicht nur passende Textstellen ab, sondern entscheidet in kleinen Schritten, ob weitere Suche, Quellenvergleich oder eine Antwort mit Zitaten sinnvoll ist.

In dieser Studie starten wir mit lokalen Collections unter `data/`. Jede Collection liegt in einem eigenen Unterordner und kann spaeter fuer unterschiedliche Anwendungen, Kunden oder Wissensbereiche stehen.

Die erste Ingestion soll Textdateien lesen, einfache Chunks erzeugen und Metadaten wie Collection, Dateipfad und Chunk-Index erhalten.
