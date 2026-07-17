export function scrollLatestUserMessageToTop(scrollRegionId) {
    const scrollRegion = document.getElementById(scrollRegionId);

    if (!scrollRegion) {
        return;
    }

    const userMessages = scrollRegion.querySelectorAll('[data-chat-role="user"]');

    if (userMessages.length === 0) {
        return;
    }

    const latestUserMessage = userMessages[userMessages.length - 1];

    const doScroll = () => {
        const regionRect = scrollRegion.getBoundingClientRect();
        const messageRect = latestUserMessage.getBoundingClientRect();

        const targetTop =
            scrollRegion.scrollTop +
            messageRect.top -
            regionRect.top;

        scrollRegion.scrollTo({
            top: Math.max(0, targetTop),
            behavior: "auto"
        });
    };

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            doScroll();

            setTimeout(doScroll, 50);
            setTimeout(doScroll, 150);
            setTimeout(doScroll, 300);
            setTimeout(doScroll, 600);
        });
    });
}