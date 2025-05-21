# Market Maker Strategy Known Issues

## Order Cancellation Rejections

### Problem Description

The market maker strategy occasionally encounters "Unknown order sent" errors when attempting to cancel orders. These errors appear in the logs as:

```
[WARN] BINANCE-TRADER-001.ExecClient-BINANCE: BinanceClientError({'code': -2011, 'msg': 'Unknown order sent.'})
[ERROR] BINANCE-TRADER-001.ExecClient-BINANCE: Failed on 'cancel_order': ClientOrderId('O-20250521-155826-001-000-59'), None
[WARN] BINANCE-TRADER-001.MarketMaker: <--[EVT] OrderCancelRejected(instrument_id=BTCUSDT.BINANCE, client_order_id=O-20250521-155826-001-000-59, venue_order_id=None, account_id=BINANCE-SPOT-master, reason='{'code': -2011, 'msg': 'Unknown order sent.'}', ts_event=1747843107337755087)
```

### Root Cause Analysis

This issue stems from a race condition between order submission and cancellation:

1. **Timing Mismatch**: The strategy attempts to cancel orders that haven't been fully processed by the exchange yet.

2. **Order Lifecycle Sequence**:
   - The strategy submits orders to the exchange
   - Before receiving confirmation that the orders are active, it may decide to cancel some of them
   - The exchange rejects these cancellation requests because the orders aren't registered yet

3. **Order Tracking Inconsistency**:
   - The strategy maintains local dictionaries (`active_buy_orders` and `active_sell_orders`) to track orders
   - These dictionaries may temporarily contain orders that don't exist on the exchange

4. **Evidence in Logs**:
   - Orders are submitted at timestamp 15:58:26.957
   - The exchange accepts some of these orders later at 15:58:27.831
   - However, cancellation requests were already sent at 15:58:26.953 (before submission)
   - This explains why the exchange responds with "Unknown order sent" errors

### Current Handling

The strategy already has mechanisms to handle these rejections:

1. **Rejection Handler**: The `handle_order_cancel_rejected` method properly removes rejected orders from tracking dictionaries:
   ```python
   def handle_order_cancel_rejected(self, event: OrderCancelRejected) -> None:
       order_id = event.client_order_id
       reason = event.reason
       self._log.warning(f"Order cancel rejected for {order_id}: {reason}")
       
       # Remove from active orders since the order is no longer valid on the exchange
       if order_id in self.active_buy_orders:
           self._log.info(f"Removing BUY order {order_id} from tracking due to cancel rejection")
           del self.active_buy_orders[order_id]
       elif order_id in self.active_sell_orders:
           self._log.info(f"Removing SELL order {order_id} from tracking due to cancel rejection")
           del self.active_sell_orders[order_id]
   ```

2. **Dictionary Cleanup**: The `_clean_order_dictionaries` method attempts to synchronize local state with exchange state:
   ```python
   def _clean_order_dictionaries(self):
       # Get all open orders from the cache for this instrument
       open_orders_ids = set()
       try:
           open_orders = self.cache.orders_open(self.instrument_id)
           open_orders_ids = {order.client_order_id for order in open_orders}
       except Exception as e:
           self._log.warning(f"Error getting open orders from cache: {e}")
       
       # Remove closed buy orders
       for order_id in list(self.active_buy_orders.keys()):
           order = self.active_buy_orders[order_id]
           # Remove if order is closed or not in the open orders cache
           if order.is_closed or (order_id not in open_orders_ids and len(open_orders_ids) > 0):
               self._log.debug(f"Removing BUY order {order_id} from tracking (closed={order.is_closed}, not_in_cache={order_id not in open_orders_ids})")
               del self.active_buy_orders[order_id]
       
       # Similar logic for sell orders...
   ```

### Impact Assessment

These errors are **not critical** and are being handled appropriately:

1. The strategy correctly removes rejected orders from its tracking dictionaries
2. This prevents further attempts to cancel non-existent orders
3. The strategy continues to function normally despite these rejections
4. These errors are common in high-frequency trading systems due to exchange latency

### Potential Improvements

While not urgent, the following improvements could reduce the frequency of these errors:

1. **Introduce Order State Tracking**: Add an additional state field to track orders that have been submitted but not yet confirmed by the exchange

2. **Delay Cancellation Requests**: Implement a short delay between order submission and potential cancellation

3. **Batch Order Operations**: Group order operations to reduce the likelihood of race conditions

4. **Enhanced Logging**: Add more detailed logging around order lifecycle to better diagnose timing issues
