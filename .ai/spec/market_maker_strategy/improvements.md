# Market Maker Strategy Improvements

```mermaid
flowchart LR
  subgraph Lifecycle
    A[PENDING_SUBMIT] -->|submit_order()| B[SUBMITTED]
    B -->|on OrderAccepted| C[ACCEPTED]
    C -->|refresh_orders → cancel| D[CANCEL_PENDING]
    D -->|on OrderCanceled| E[CANCELLED]
    D -->|on OrderCancelRejected| F[REJECTED]
  end
```

1. Define an `OrderState` enum and a `TrackedOrder` dataclass next to your imports:
   ```python
   from enum import Enum
   from dataclasses import dataclass

   class OrderState(Enum):
       SUBMITTED = "SUBMITTED"
       ACCEPTED = "ACCEPTED"
       CANCEL_PENDING = "CANCEL_PENDING"

   @dataclass
   class TrackedOrder:
       order: LimitOrder
       state: OrderState
   ```
2. Change `active_buy_orders` and `active_sell_orders` to map `ClientOrderId` → `TrackedOrder` instead of bare `LimitOrder`.
3. In `_place_limit_order`, after `self.submit_order(order)`, add:
   ```python
   self.active_buy_orders[order.client_order_id] = TrackedOrder(order, OrderState.SUBMITTED)
   ```
   (Similarly for sell orders.)
4. In `on_event`, handle:
   - `OrderAccepted`: set `.state = OrderState.ACCEPTED` and store `venue_order_id`.
   - `OrderCanceled` and `OrderCancelRejected`: transition or remove the tracked order.
5. In `refresh_orders`, before cancelling:
   - Only cancel if `tracked_order.state == OrderState.ACCEPTED` **and** `venue_order_id` appears in `cache.orders_open(...)`.
   - After `cancel_order()`, set `tracked_order.state = OrderState.CANCEL_PENDING`.
6. Update `_clean_order_dictionaries` to remove any tracked order that is:
   - in `CANCELLED` or `REJECTED` state,
   - closed,
   - or missing from the open-orders cache.
7. Update `problems.md` under “Potential Improvements”:
   > **1.** Introduce explicit order-state tracking — only issue cancellation once `OrderAccepted` arrives and `venue_order_id` is confirmed in the exchange’s order cache.