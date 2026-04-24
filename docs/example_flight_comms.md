# Example ATC Communication Flow — LIML → LIRF

**Flight**: RYR2NM (Ryanair Two November Mike)  
**Route**: Milano Linate (LIML) → Roma Fiumicino (LIRF)  
**SID**: OPTO1E, Runway 36  
**STAR**: GINA2A, Runway 16L  
**Cruise**: FL180  

---

## 1 — Clearance Delivery (121.8 MHz)

> **Pilot**: Milano Clearance, Ryanair Two November Mike, request IFR clearance to Roma Fiumicino.

> **ATC**: Ryanair Two November Mike, Milano clearance delivery, cleared to Roma Fiumicino airport, via OPTO ONE ECHO departure, runway three six, climb via SID to flight level one eight zero, squawk four three one five, QNH one zero one three, departure frequency one two five decimal niner.

> **Pilot**: Cleared to Roma Fiumicino, OPTO ONE ECHO departure, runway three six, climb via SID flight level one eight zero, squawk four three one five, QNH one zero one three, departure one two five decimal niner, Ryanair Two November Mike.

> **ATC**: Ryanair Two November Mike, readback correct, contact ground one two one decimal niner when ready.

---

## 2 — Ground (121.9 MHz) — pre-departure

> **Pilot**: Milano Ground, Ryanair Two November Mike, stand Charlie four, request startup and pushback.

> **ATC**: Ryanair Two November Mike, Milano ground, startup approved, pushback approved, face north.

> **Pilot**: Startup approved, pushback approved, face north, Ryanair Two November Mike.

*(pushback complete, engines running)*

> **Pilot**: Milano Ground, Ryanair Two November Mike, ready to taxi.

> **ATC**: Ryanair Two November Mike, taxi to holding point Romeo one, runway three six, via taxiway Bravo, Hotel, hold short of runway two eight.

> **Pilot**: Taxi to holding point Romeo one, runway three six, via Bravo, Hotel, hold short runway two eight, Ryanair Two November Mike.

*(crossing runway 28 — if required)*

> **ATC**: Ryanair Two November Mike, runway two eight, cross immediately.

> **Pilot**: Crossing runway two eight, Ryanair Two November Mike.

*(at holding point)*

> **Pilot**: Milano Ground, Ryanair Two November Mike, holding point Romeo one, runway three six, ready.

> **ATC**: Ryanair Two November Mike, contact tower one one eight decimal seven.

> **Pilot**: Tower one one eight decimal seven, Ryanair Two November Mike.

---

## 3 — Tower (118.7 MHz) — departure

> **Pilot**: Milano Tower, Ryanair Two November Mike, holding point Romeo one, runway three six, ready for departure.

> **ATC**: Ryanair Two November Mike, Milano tower, wind calm, runway three six, line up and wait.

> **Pilot**: Line up and wait, runway three six, Ryanair Two November Mike.

> **ATC**: Ryanair Two November Mike, wind calm, runway three six, cleared for takeoff.

> **Pilot**: Cleared for takeoff, runway three six, Ryanair Two November Mike.

*(airborne, passing 1000 ft AAL)*

> **ATC**: Ryanair Two November Mike, contact departure one two five decimal niner.

> **Pilot**: Departure one two five decimal niner, Ryanair Two November Mike.

---

## 4 — Departure (125.9 MHz) — SID climb

> **Pilot**: Milano Departure, Ryanair Two November Mike, passing two thousand, climbing flight level one eight zero, OPTO ONE ECHO departure.

> **ATC**: Ryanair Two November Mike, Milano departure, radar contact, climb flight level one eight zero, report reaching.

> **Pilot**: Climb flight level one eight zero, wilco, Ryanair Two November Mike.

*(at FL180)*

> **Pilot**: Milano Departure, Ryanair Two November Mike, level flight level one eight zero.

> **ATC**: Ryanair Two November Mike, roger, proceed direct SOGMI, contact Roma Control on one three five decimal eight.

> **Pilot**: Direct SOGMI, one three five decimal eight, Ryanair Two November Mike.

---

## 5 — En-route (135.8 MHz) — cruise

*(Not simulated in this app — handled by real-world ATCC or skipped)*

---

## 6 — Approach (119.2 MHz) — STAR and approach

> **Pilot**: Roma Approach, Ryanair Two November Mike, flight level one eight zero, inbound via GINA TWO ALFA.

> **ATC**: Ryanair Two November Mike, Roma approach, radar contact, descend flight level one one zero, expect ILS approach runway one six left.

> **Pilot**: Descend flight level one one zero, Ryanair Two November Mike.

> **ATC**: Ryanair Two November Mike, descend altitude three thousand feet, QNH one zero one five.

> **Pilot**: Descend three thousand, QNH one zero one five, Ryanair Two November Mike.

> **ATC**: Ryanair Two November Mike, turn left heading one two zero, intercept ILS runway one six left.

> **Pilot**: Left heading one two zero, ILS runway one six left, Ryanair Two November Mike.

> **ATC**: Ryanair Two November Mike, ILS runway one six left, cleared ILS approach runway one six left, contact tower one one nine decimal two.

> **Pilot**: Cleared ILS runway one six left, one one nine decimal two, Ryanair Two November Mike.

---

## 7 — Tower (119.2 MHz) — landing

> **Pilot**: Roma Tower, Ryanair Two November Mike, ILS one six left, fully established.

> **ATC**: Ryanair Two November Mike, Roma tower, wind one eight zero degrees five knots, runway one six left, cleared to land.

> **Pilot**: Cleared to land, runway one six left, Ryanair Two November Mike.

*(after touchdown)*

> **ATC**: Ryanair Two November Mike, turn right next taxiway, contact ground one two one decimal eight.

> **Pilot**: Right next taxiway, ground one two one decimal eight, Ryanair Two November Mike.

---

## 8 — Ground (121.8 MHz) — post-landing taxi

> **Pilot**: Roma Ground, Ryanair Two November Mike, runway one six left vacated, request taxi to gate.

> **ATC**: Ryanair Two November Mike, Roma ground, taxi to apron Delta, stand Delta seven, via taxiway Foxtrot, Golf.

> **Pilot**: Apron Delta, stand Delta seven, via Foxtrot, Golf, Ryanair Two November Mike.

---

## Controller summary

| Phase              | Controller        | Frequency  | Key tasks                                         |
|--------------------|-------------------|------------|---------------------------------------------------|
| Pre-departure      | Clearance Delivery| 121.8 MHz  | IFR clearance, SID, squawk, QNH                   |
| Startup & taxi     | Ground (dep)      | 121.9 MHz  | Startup, pushback, taxi route, runway crossings   |
| Takeoff & climb    | Tower (dep)       | 118.7 MHz  | Line up, takeoff clearance, initial climb handoff |
| SID climb          | Departure         | 125.9 MHz  | SID tracking, climb to cruise, en-route handoff   |
| En-route           | *(not simulated)* | —          | —                                                 |
| Descent & approach | Approach          | 119.2 MHz  | STAR, descent, ILS intercept, approach clearance  |
| Landing            | Tower (arr)       | 119.2 MHz  | Landing clearance, vacate instruction             |
| Taxi to gate       | Ground (arr)      | 121.8 MHz  | Taxi route to stand                               |
