using System.Text.Json.Serialization;
using Microsoft.Extensions.VectorData;

namespace Policy_Pilot_P2.Services;

public class IngestedChunk
{
    public const int VectorDimensions = 768; // 768 is the default vector size for embeddinggemma:300m
    public const string VectorDistanceFunction = DistanceFunction.CosineDistance;
    public const string CollectionName = "data-policy_pilot_p2-chunks";

    [VectorStoreKey(StorageName = "key")]
    [JsonPropertyName("key")]
    public required Guid Key { get; set; }

    [VectorStoreData(StorageName = "documentid")]
    [JsonPropertyName("documentid")]
    public required string DocumentId { get; set; }

    [VectorStoreData(StorageName = "content")]
    [JsonPropertyName("content")]
    public required string Text { get; set; }

    [VectorStoreData(StorageName = "context")]
    [JsonPropertyName("context")]
    public string? Context { get; set; }

    [VectorStoreVector(VectorDimensions, DistanceFunction = VectorDistanceFunction, StorageName = "embedding")]
    [JsonPropertyName("embedding")]
    public string? Vector => $"""
    Source file: {DocumentId}

    Policy excerpt:
    {Text}
    """;
}
