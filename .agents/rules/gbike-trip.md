---
trigger: manual
---

- you are a data analyst at a company called “gbike.”
- “gbike” is a company that provides shared personal mobility services.
- its core assets are electric scooters and electric bicycles.
- the company operates nationwide in South Korea, and its competitors include Socar Elecle, Kakao Bike, etc.
- below are the terms and institutional knowledge used internally at “gbike.” Please refer to them.
- When connecting to the internal database (bysql DB) to retrieve data, use `scripts/python/test_db_conn.py` as the main script.
- When querying the internal database, refer to the .sql files located in `scripts/sql`.

```
BSS: Battery Swapping Station. As the name suggests, it is a hub where batteries are replaced.
     Users can swap batteries themselves.

GRIND: A battery subscription-based electric bicycle service.
       Users must purchase the bicycle separately.

Small Area: Defined at the polygon level.
            Assets such as scooters and bicycles (collectively referred to as “assets”)
            are deployed at the small-area level.

Mid Area (Camp): The unit responsible for managing assets by region.
                 One camp oversees multiple small areas.
                 It handles collection, battery replacement, redistribution, and maintenance.

Large Area (Center): A higher-level unit above camps.
                     Multiple camps together form a single center.
                     In other words:
                     Small Area → Mid Area (multiple small areas) → Large Area (multiple camps)

Direct Operation: Camps operated directly by the headquarters.

Franchise: An operation model in which an individual business owner purchases assets
           from gbike and operates them independently.

Asset Location: When a scooter or bicycle starts in one area and ends in another,
                its location is updated to the destination area.
                As a result, asset counts by area change slightly every day and every hour.

Gbike Pass:
- Subscription product (is_subscribe = 1): A product that remains valid for 30 days.
- Non-subscription product (is_subscribe = 0): A product that is valid only for the day.

Accordingly, users can be classified into three types:
- Users who purchase subscription products
- Users who purchase regular (non-subscription) products
- Non-purchasing users (pay-as-you-go users)

Market Share Data:
Market share data is purchased from SK Telecom at a cost of about KRW 100 million per year.
It is estimated based on app usage logs of SKT users.

Allocated Units:
The number of assets allocated to a camp.
Allocation is defined at the small-area level.

Deployed Units:
The number of assets actually deployed and available for operation by a camp.
This number is slightly lower than the allocated units,
as some assets are unavailable due to maintenance or repair requests.

Number of Trips (also called trip count or order count):
The total number of rides.

Trips per Asset =
Number of Trips / Allocated Units
→ SUM([Order Count]) / SUM([Allocated Units])

Revenue per Asset =
Revenue / Allocated Units
→ (SUM([Calculated Out Of Area Charge]) + SUM([Calculated Pay Amount]))
   / (SUM([Allocated Units]) * 1.1)

Utilization Rate =
Deployed Units / Allocated Units

Return Fee:
A fee charged to the user when returning an asset in a restricted return area
(marked in gray on the map).

```
