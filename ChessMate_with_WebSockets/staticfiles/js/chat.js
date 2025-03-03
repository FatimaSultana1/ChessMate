const chatSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/chat/'
);

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    document.querySelector('#chat-log').innerHTML += (data.message + '<br>');
};

document.querySelector('#chat-message-submit').onclick = function(e) {
    const messageInputDom = document.querySelector('#chat-message-input');
    const message = `${username}: ${messageInputDom.value}`; // Prepend username
    chatSocket.send(JSON.stringify({ 'message': message }));
    messageInputDom.value = '';
};
