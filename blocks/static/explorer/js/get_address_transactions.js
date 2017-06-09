/**
 * Created by sammoth on 09/06/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/get_address_transactions/');

    var address = $("#address").text();

    var transactions_div = $("#transactions");

    webSocketBridge.socket.addEventListener('open', function() {
        webSocketBridge.stream(address).send({'host': window.location.hostname});
        webSocketBridge.listen(function(data, channel) {
            console.log(data);
            transactions_div.append(data["html"]);
        });
    });
});
