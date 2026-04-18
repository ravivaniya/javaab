import os
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticSearch, SemanticPrioritizedFields,
    SemanticField
)
from azure.core.credentials import AzureKeyCredential

load_dotenv()

client = SearchIndexClient(
    endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_KEY"))
)

# --- INDEX 1: textbook_chunks ---
chunks_index = SearchIndex(
    name="textbook_chunks",
    fields=[
        SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=1536, vector_search_profile_name="hnsw-profile"),
        SimpleField(name="board", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="class_level", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
        SimpleField(name="subject", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="chapter_number", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="chapter_name", type=SearchFieldDataType.String),
        SearchableField(name="topic", type=SearchFieldDataType.String),
        SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="source_book", type=SearchFieldDataType.String),
        SimpleField(name="page_number", type=SearchFieldDataType.Int32),
    ],
    vector_search=VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo", parameters={"m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine"})],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")]
    ),
    semantic_search=SemanticSearch(
        configurations=[SemanticConfiguration(
            name="semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")],
                keywords_fields=[SemanticField(field_name="topic"), SemanticField(field_name="chapter_name")]
            )
        )]
    )
)

# --- INDEX 2: verified_answers ---
cache_index = SearchIndex(
    name="verified_answers",
    fields=[
        SimpleField(name="cache_id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="question", type=SearchFieldDataType.String),
        SearchField(name="question_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=1536, vector_search_profile_name="hnsw-profile"),
        SimpleField(name="board", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="class_level", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="subject", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="chapter_number", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="chapter_name", type=SearchFieldDataType.String),
        SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="answer_en", type=SearchFieldDataType.String),
        SearchableField(name="answer_hi", type=SearchFieldDataType.String),
        SearchableField(name="answer_gu", type=SearchFieldDataType.String),
        SearchableField(name="source_citation", type=SearchFieldDataType.String),
        SimpleField(name="verified_by", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="verified_at", type=SearchFieldDataType.DateTimeOffset, filterable=True),
    ],
    vector_search=VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo", parameters={"m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine"})],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")]
    )
)

for index in [chunks_index, cache_index]:
    result = client.create_or_update_index(index)
    print(f"✅ Index created: {result.name}")