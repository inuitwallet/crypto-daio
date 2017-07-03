/**
 * Created by sammoth on 09/06/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/get_block_transactions/');

    var block_hash = $("#block-hash").text();

    var transactions_div = $("#transactions");

    webSocketBridge.socket.addEventListener('open', function() {
        webSocketBridge.stream(block_hash).send({'host': window.location.hostname});
        webSocketBridge.listen(function(data) {
            console.log(data);
            if (data["message_type"] === "block_transaction"){
                transactions_div.append(data["html"]);
            }
        });
    });
});
