using Microsoft.Extensions.AI;
using Microsoft.Extensions.DataIngestion;
using Microsoft.Extensions.DataIngestion.Chunkers;
using Microsoft.Extensions.VectorData;
using Microsoft.ML.Tokenizers;

namespace Policy_Pilot_P2.Services.Ingestion;

public class DataIngestor(
    ILogger<DataIngestor> logger,
    ILoggerFactory loggerFactory,
    VectorStore vectorStore,
    IEmbeddingGenerator<string, Embedding<float>> embeddingGenerator)
{
    public async Task IngestDataAsync(DirectoryInfo directory, string searchPattern)
    {
        using var writer = new VectorStoreWriter<string>(vectorStore, dimensionCount: IngestedChunk.VectorDimensions, new()
        {
            CollectionName = IngestedChunk.CollectionName,
            DistanceFunction = IngestedChunk.VectorDistanceFunction,
            IncrementalIngestion = true,//avoids reproessing when the DB already exists. If change embedding models/vector dimension/text/, make sure to delete App_Data/vector-store.db and rebuild.
        });

        using var pipeline = new IngestionPipeline<string>(
            reader: new DocumentReader(directory),
            chunker: new SemanticSimilarityChunker(embeddingGenerator, new(TiktokenTokenizer.CreateForModel("gpt-4o"))),
            writer: writer,
            loggerFactory: loggerFactory);

        await foreach (var result in pipeline.ProcessAsync(directory, searchPattern))
        {
            logger.LogInformation("Completed processing '{id}'. Succeeded: '{succeeded}'.", result.DocumentId, result.Succeeded);
        }
    }
}
