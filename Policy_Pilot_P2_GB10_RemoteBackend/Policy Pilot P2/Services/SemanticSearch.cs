using Policy_Pilot_P2.Services.Ingestion;
using Microsoft.Extensions.VectorData;

namespace Policy_Pilot_P2.Services;

public class SemanticSearch(
    VectorStoreCollection<string, IngestedChunk> vectorCollection,
    [FromKeyedServices("ingestion_directory")] DirectoryInfo ingestionDirectory,
    DataIngestor dataIngestor)
{
    private Task? _ingestionTask;

    public async Task BuildIndexAsync()
        => await (_ingestionTask ??= dataIngestor.IngestDataAsync(ingestionDirectory, searchPattern: "*.*"));

    public async Task<IReadOnlyList<IngestedChunk>> SearchAsync(string text, string documentIdFilter, int maxResults)
    {
        var nearest = vectorCollection.SearchAsync(text, maxResults, new VectorSearchOptions<IngestedChunk>
        {
            Filter = !string.IsNullOrWhiteSpace(documentIdFilter)
                ? record => record.DocumentId == documentIdFilter
                : null,
        });

        return await nearest.Select(result => result.Record).ToListAsync();
    }
}