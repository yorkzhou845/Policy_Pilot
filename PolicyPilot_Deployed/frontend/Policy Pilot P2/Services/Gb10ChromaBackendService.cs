using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace Policy_Pilot_P2.Services;

public sealed class Gb10ChromaBackendService(
    HttpClient httpClient,
    IConfiguration configuration,
    ILogger<Gb10ChromaBackendService> logger)
{
    private static readonly Regex CitationTagRegex = new(
        "<citation\\s+filename=[\\'\"].*?[\\'\"].*?</citation>",
        RegexOptions.IgnoreCase | RegexOptions.Singleline);

    private static readonly Regex SourcesUsedNoneRegex = new(
        @"Sources\s+used\s*:\s*(?:\r?\n\s*)?[-*]?\s*None\b",
        RegexOptions.IgnoreCase);

    private readonly string _baseUrl = NormalizeBaseUrl(
        configuration["GB10Backend:BaseUrl"]
        ?? Environment.GetEnvironmentVariable("GB10_BACKEND_BASE_URL")
        ?? "http://66.230.43.54:8090");

    private readonly string? _apiKey = FirstNonEmpty(
        configuration["GB10Backend:ApiKey"],
        Environment.GetEnvironmentVariable("GB10_BACKEND_API_KEY"));

    public async Task<string> GetAnswerAsync(
        string question,
        UserRuntimeContext? runtimeContext = null,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(question))
        {
            return "Please enter a policy question.";
        }

        runtimeContext ??= new UserRuntimeContext
        {
            CurrentDateTimeLocal = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
            CurrentDateIsoUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            TimeZone = TimeZoneInfo.Local.Id,
            Location = "Lubbock"
        };

        var response = await PostAsync<AnswerResponse>(
            "answer",
            new AnswerRequest(question, runtimeContext),
            cancellationToken);

        if (!string.IsNullOrWhiteSpace(response.Error))
        {
            logger.LogWarning("GB10 backend returned an error: {Error}", response.Error);
            return response.Error!;
        }

        if (string.IsNullOrWhiteSpace(response.Answer))
        {
            return "The GB10 backend returned an empty answer.";
        }

        return CleanCitationsForNoSourceAnswer(response.Answer!);
    }

    public async Task BuildIndexAsync(CancellationToken cancellationToken = default)
    {
        var response = await PostAsync<IngestResponse>("ingest", new { }, cancellationToken);

        if (!string.IsNullOrWhiteSpace(response.Error))
        {
            throw new InvalidOperationException(response.Error);
        }
    }

    private async Task<TResponse> PostAsync<TResponse>(
        string relativePath,
        object payload,
        CancellationToken cancellationToken)
        where TResponse : class, new()
    {
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"{_baseUrl}/{relativePath.TrimStart('/')}");

        request.Content = JsonContent.Create(payload);

        if (!string.IsNullOrWhiteSpace(_apiKey))
        {
            request.Headers.TryAddWithoutValidation("X-API-KEY", _apiKey);
        }

        HttpResponseMessage response;

        try
        {
            response = await httpClient.SendAsync(request, cancellationToken);
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
        {
            logger.LogError(ex, "Could not connect to the GB10 backend at {BaseUrl}", _baseUrl);
            return ErrorResponse<TResponse>($"Could not connect to the GB10 backend at {_baseUrl}.");
        }

        var body = await response.Content.ReadAsStringAsync(cancellationToken);

        if (response.StatusCode == HttpStatusCode.Unauthorized || response.StatusCode == HttpStatusCode.Forbidden)
        {
            return ErrorResponse<TResponse>("The GB10 backend rejected the request. Check GB10Backend__ApiKey on the web app and POLICY_PILOT_BACKEND_API_KEY on GB10.");
        }

        if (!response.IsSuccessStatusCode)
        {
            logger.LogError(
                "GB10 backend failed with HTTP {StatusCode}. Body: {Body}",
                (int)response.StatusCode,
                body);

            return ErrorResponse<TResponse>($"The GB10 backend failed with HTTP {(int)response.StatusCode}.");
        }

        try
        {
            return JsonSerializer.Deserialize<TResponse>(
                    body,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
                ?? ErrorResponse<TResponse>("The GB10 backend returned empty JSON.");
        }
        catch (JsonException ex)
        {
            logger.LogError(ex, "Could not parse GB10 backend response. Body: {Body}", body);
            return ErrorResponse<TResponse>("Could not parse the GB10 backend response.");
        }
    }

    private static TResponse ErrorResponse<TResponse>(string message)
        where TResponse : class, new()
    {
        return typeof(TResponse) switch
        {
            var t when t == typeof(AnswerResponse) => (new AnswerResponse(null, message) as TResponse)!,
            var t when t == typeof(IngestResponse) => (new IngestResponse("error", message) as TResponse)!,
            _ => new TResponse()
        };
    }

    private static string CleanCitationsForNoSourceAnswer(string answer)
    {
        if (!IsNoSourceAnswer(answer))
        {
            return answer.Trim();
        }

        var cleaned = CitationTagRegex.Replace(answer, string.Empty);
        cleaned = Regex.Replace(cleaned, @"\n{3,}", "\n\n").Trim();

        return cleaned;
    }

    private static bool IsNoSourceAnswer(string answer)
    {
        return answer.Contains("I do not know based on the provided policy content", StringComparison.OrdinalIgnoreCase)
            || SourcesUsedNoneRegex.IsMatch(answer);
    }

    private static string NormalizeBaseUrl(string value)
    {
        var cleaned = string.IsNullOrWhiteSpace(value)
            ? "http://66.230.43.54:8090"
            : value.Trim();

        return cleaned.TrimEnd('/');
    }

    private static string? FirstNonEmpty(params string?[] values)
    {
        foreach (var value in values)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                return value.Trim();
            }
        }

        return null;
    }

    private sealed record AnswerRequest(string Question, UserRuntimeContext RuntimeContext);

    private sealed class AnswerResponse
    {
        public AnswerResponse()
        {
        }

        public AnswerResponse(string? answer, string? error)
        {
            Answer = answer;
            Error = error;
        }

        public string? Answer { get; set; }
        public string? Error { get; set; }
    }

    private sealed class IngestResponse
    {
        public IngestResponse()
        {
        }

        public IngestResponse(string? status, string? error)
        {
            Status = status;
            Error = error;
        }

        public string? Status { get; set; }
        public string? Error { get; set; }
    }
}
