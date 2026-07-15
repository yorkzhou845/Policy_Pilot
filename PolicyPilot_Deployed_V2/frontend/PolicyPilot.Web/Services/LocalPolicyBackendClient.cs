using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace PolicyPilot.Web.Services;

public sealed class LocalPolicyBackendClient(HttpClient httpClient)
{
    public async Task<PolicyAnswer> AskAsync(
        string question,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "answer",
            new AnswerRequest(question),
            cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            var body = await response.Content.ReadAsStringAsync(cancellationToken);
            var detail = TryReadDetail(body) ?? response.ReasonPhrase ?? "Unknown backend error";
            throw new InvalidOperationException(detail);
        }

        var payload = await response.Content.ReadFromJsonAsync<AnswerResponse>(
            cancellationToken: cancellationToken);

        if (payload is null || string.IsNullOrWhiteSpace(payload.Answer))
        {
            throw new InvalidOperationException("The local backend returned an empty response.");
        }

        return new PolicyAnswer(payload.Answer, payload.Citations ?? []);
    }

    private static string? TryReadDetail(string body)
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            if (!document.RootElement.TryGetProperty("detail", out var detail))
            {
                return null;
            }

            return detail.ValueKind == JsonValueKind.String
                ? detail.GetString()
                : detail.ToString();
        }
        catch (JsonException)
        {
            return string.IsNullOrWhiteSpace(body) ? null : body;
        }
    }

    private sealed record AnswerRequest(string Question);
    private sealed record AnswerResponse(string Answer, List<SourceCitation>? Citations);
}

public sealed record PolicyAnswer(string Answer, IReadOnlyList<SourceCitation> Citations);

public sealed record SourceCitation(
    [property: JsonPropertyName("source_file")] string SourceFile,
    [property: JsonPropertyName("quote")] string Quote,
    [property: JsonPropertyName("score")] double Score);
