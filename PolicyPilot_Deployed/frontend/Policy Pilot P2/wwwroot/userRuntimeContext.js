window.userRuntimeContext = {
    get: function () {
        const now = new Date();

        const pad = (value) => String(value).padStart(2, "0");
        const localDateTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

        return {
            currentDateTimeLocal: localDateTime,
            currentDateIsoUtc: now.toISOString(),
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Unknown",
            location: "Lubbock"
        };
    }
};
