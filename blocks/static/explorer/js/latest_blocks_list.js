/**
 * Created by sammoth on 08/05/17.
 */
const webSocketBridge = new channels.WebSocketBridge();
webSocketBridge.connect('/latest_blocks_list/');
webSocketBridge.listen(function(action, stream) {
  console.log(action, stream);
});
