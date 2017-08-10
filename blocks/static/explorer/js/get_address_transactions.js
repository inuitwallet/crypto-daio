/**
 * Created by sammoth on 09/06/17.
 */
$(function() {
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/get_address_details/');

    var address = $("#address").text();

    var balance_div = $("#balance");
    var transactions_div = $("#transactions");
    var tx_total = $("#tx_total");
    var tx_index = $("#tx_index");

    webSocketBridge.socket.addEventListener('open', function() {
        webSocketBridge.stream(address).send({'host': window.location.hostname});
        webSocketBridge.listen(function(data, channel) {
            if (data["message_type"] === "address_total_tx") {
                tx_total.text(data["value"]);
            }
            if (data["message_type"] === "address_transaction") {
                transactions_div.append(data["html"]);
                tx_index.text(data["index"]);
            }
            if (data["message_type"] === "address_balance") {
                balance_div.text(data["balance"]);
            }
        });
    });
});
