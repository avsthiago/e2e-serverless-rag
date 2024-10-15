from typing import List, Union
from fasthtml.common import (
    fast_app, serve, to_xml, Script, Link,
    Div, H1, Form, Textarea, Button, Img, Hidden, Title, NotStr
)  # fmt: skip
from starlette.responses import StreamingResponse
import asyncio
from rag import retrieve, generate_response, cached_table
import base64

# Set up the app, including DaisyUI and Tailwind CSS for styling
app, rt = fast_app(
    ct_hdr=True,
    hdrs=[
        Script(
            src="https://unpkg.com/htmx-ext-transfer-encoding-chunked@0.4.0/transfer-encoding-chunked.js"
        ),
        Script(src="https://cdn.jsdelivr.net/npm/js-sha256@0.9.0/build/sha256.min.js"),
        Script(src="https://cdn.tailwindcss.com"),
        Link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/daisyui@2.51.5/dist/full.css",
        ),
    ],
    debug=True,
)


# Chat message component (renders a chat bubble with an avatar)
def ChatMessage(msg, user, id=None):
    bubble_class = "chat-bubble-primary" if user else "chat-bubble-secondary"
    chat_class = "chat-end" if user else "chat-start"
    avatar_src = (
        "https://i.pravatar.cc/50?img=4" if user else "https://i.pravatar.cc/50?img=7"
    )

    return Div(cls=f"chat {chat_class} mb-4", id=f"msg-{id}")(
        Div(cls="chat-image avatar")(Img(src=avatar_src, cls="w-10 rounded-full")),
        Div("You" if user else "Bot", cls="chat-header"),
        Div(
            msg,
            cls=f"chat-bubble {bubble_class}",
            id=f"msg-{id}-content" if id else None,
        ),
        Hidden(
            msg,
            name="messages",
            id=f"msg-{id}-hidden" if id else None,
        ),
    )


def ChatInput():
    return Textarea(
        name="msg",
        id="msg-input",
        placeholder="Type your message...",
        cls="textarea textarea-bordered w-full resize-none",
        rows="1",
    )


@rt("/")
def index():
    page = (
        Title("Talk To My House 🏠"),
        Div(cls="p-4 max-w-3xl mx-auto bg-base-200 min-h-screen")(
            H1("Talk To My House 🏠", cls="text-center text-2xl font-bold mb-4"),
            Div(cls="bg-base-100 rounded-lg shadow-lg p-6 flex flex-col h-[90vh]")(
                Form(
                    hx_post=send,
                    hx_target="#chatlist",
                    hx_swap="beforeend",
                    hx_ext="chunked-transfer",
                    hx_disabled_elt="#msg-group",
                    cls="flex flex-col h-full",
                    enctype="application/x-www-form-urlencoded",
                )(
                    Div(
                        id="chatlist",
                        cls="flex-1 overflow-auto mb-4",
                    ),
                    Div(cls="flex items-center", id="msg-group")(
                        ChatInput(),
                        Button(
                            "Send",
                            cls="btn btn-primary btn-sm ml-4",
                            type="submit",
                            style="width: unset; margin-bottom: unset; padding-top: unset; padding-bottom: unset;",
                        ),
                    ),
                )
            ),
            Script("""document.addEventListener('DOMContentLoaded', function () {
                        const msgInput = document.getElementById('msg-input');

                        // Function to auto-resize the textarea
                        msgInput.addEventListener('input', function () {
                            this.style.height = 'auto';
                            this.style.height = this.scrollHeight + 'px';
                        });

                        // Allow sending message with Enter key
                        msgInput.addEventListener('keypress', function (e) {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                document.querySelector('button[type="submit"]').click();
                            }
                        });
                   
                        document.querySelector('form').addEventListener('htmx:afterRequest', function (event) {
                            document.getElementById('msg-input').value = '';
                        });
                   
                        document.body.addEventListener('htmx:configRequest', function(event) {
                            var verb = event.detail.verb.toUpperCase();
                            if (verb === 'POST' || verb === 'PUT') {
                                var elt = event.detail.elt;
                                var form = elt.closest('form');
                                if (!form) {
                                    console.error('Form not found for element:', elt);
                                    return;
                                }

                                var formData = new FormData(form);
                                var newParameters = {};

                                for (var pair of formData.entries()) {
                                    var key = pair[0];
                                    var value = pair[1];
                                    // Base64-encode the value
                                    var encodedValue = btoa(unescape(encodeURIComponent(value)));

                                    if (newParameters[key]) {
                                        // If key already exists, ensure it's an array and add the new value
                                        if (Array.isArray(newParameters[key])) {
                                            newParameters[key].push(encodedValue);
                                        } else {
                                            newParameters[key] = [newParameters[key], encodedValue];
                                        }
                                    } else {
                                        newParameters[key] = encodedValue;
                                    }
                                }

                                // Update the parameters to be sent in the request
                                event.detail.parameters = newParameters;

                                // Recompute the body for hashing
                                var urlSearchParams = new URLSearchParams();
                                for (var key in newParameters) {
                                    var value = newParameters[key];
                                    if (Array.isArray(value)) {
                                        value.forEach(function(val) {
                                            urlSearchParams.append(key, val);
                                        });
                                    } else {
                                        urlSearchParams.append(key, value);
                                    }
                                }

                                var body = urlSearchParams.toString();
                                var hash = sha256(body);
                                event.detail.headers['x-amz-content-sha256'] = hash;
                            }
                        });

                        // Function to scroll the chat window to the bottom
                        function scrollChatToBottom() {
                            var chatList = document.getElementById('chatlist');
                            if (chatList) {
                                chatList.scrollTop = chatList.scrollHeight;
                            }
                        }

                        // Scroll the chat window to the bottom after new content is added
                        document.addEventListener('htmx:oobAfterSwap', ({ detail }) => {
                            if (detail?.target?.id?.match(/^msg-\\d+-content$/)) {
                                scrollChatToBottom();
                            }
                        });
                    });
            """),
        ),
    )
    return page


async def stream_response(msg, messages):
    # Yield the user's message
    yield to_xml(ChatMessage(msg, True, id=len(messages) - 1))
    # Start the bot's message with empty content
    yield to_xml(ChatMessage("", False, id=len(messages)))

    # We only load the table here to avoid cold start
    # The first request will be slower than the rest
    table = await cached_table()
    chunks = await retrieve(msg, table)

    bot_response = ""
    for i in generate_response(msg, chunks, messages):
        bot_response += i.replace("\n", "<br />")
        yield to_xml(
            Div(
                NotStr(bot_response),
                cls="chat-bubble chat-bubble-secondary",
                id=f"msg-{len(messages)}-content",
                hx_swap_oob="outerHTML",
            )
        )
        # Apparently we need this to make the response stream
        await asyncio.sleep(0)

    messages.append(bot_response)

    yield to_xml(
        Hidden(
            bot_response,
            name="messages",
            id=f"msg-{len(messages)-1}-hidden",
            hx_swap_oob="outerHTML",
        )
    )


# Handle the form submission
@app.post
async def send(msg: str, messages: List[str] = None):
    if not msg:
        return

    msg = base64.b64decode(msg).decode()

    if messages is not None:
        messages = [base64.b64decode(i).decode() for i in messages]
    else:
        messages = []

    messages.append(msg.rstrip())

    return StreamingResponse(
        stream_response(msg, messages),
        media_type="text/plain",
        headers={"X-Transfer-Encoding": "chunked"},
    )


serve(port=8000, reload=True)
