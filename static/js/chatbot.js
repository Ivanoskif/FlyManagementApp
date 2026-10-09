document.addEventListener("DOMContentLoaded", () => {
    const widget = document.getElementById("ai-chat-widget");

    if (!widget) {
        return;
    }

    const endpoint = widget.dataset.endpoint;

    const panel = document.getElementById("ai-chat-panel");
    const toggle = document.getElementById("ai-chat-toggle");
    const close = document.getElementById("ai-chat-close");

    const form = document.getElementById("ai-chat-form");
    const input = document.getElementById("ai-chat-input");
    const messages = document.getElementById("ai-chat-messages");

    const csrfToken = form.querySelector(
        'input[name="csrfmiddlewaretoken"]'
    ).value;


    function addMessage(text, type) {
        const message = document.createElement("div");

        message.className = `ai-chat-message ${type}`;
        message.textContent = text;

        messages.appendChild(message);

        messages.scrollTop = messages.scrollHeight;

        return message;
    }


    toggle.addEventListener("click", () => {
        panel.classList.toggle("d-none");

        if (!panel.classList.contains("d-none")) {
            input.focus();
        }
    });


    close.addEventListener("click", () => {
        panel.classList.add("d-none");
    });


    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const text = input.value.trim();

        if (!text) {
            return;
        }

        addMessage(text, "user");

        input.value = "";

        input.disabled = true;

        const sendButton = form.querySelector(
            'button[type="submit"]'
        );

        sendButton.disabled = true;

        const loading = addMessage(
            "Searching...",
            "bot"
        );


        try {
            const response = await fetch(endpoint, {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },

                body: JSON.stringify({
                    message: text,
                }),
            });


            const data = await response.json();

            loading.remove();


            if (!response.ok) {
                addMessage(
                    data.error || "Something went wrong.",
                    "error"
                );

                return;
            }

            addMessage(
                data.answer,
                "bot"
            );

        } catch (error) {

            loading.remove();

            addMessage(
                "Unable to connect to the assistant.",
                "error"
            );

        } finally {

            input.disabled = false;
            sendButton.disabled = false;

            input.focus();
        }
    });
});