Current Known Bugs

1\. leadership\_email.py Watchlist parsing



Current output:

Watchlist:

 

\---------

Voucherify...



Bug:

\_extract\_watchlist()



is including the underline from:

WATCHOUTS

\---------



Expected:


Watchlist:

 

Voucherify...



Status: OPEN



\-------------------------------------------



Current enhancements



2\. Write leadership\_email.txt



Current state:

generate\_leadership\_email(...)



returns a rendered string only.



Not yet:

leadership\_email.txt



Status: NEXT



\---------------------------------------------



3\. Integrate leadership\_email into runner



Current pipeline:

1. Executive Summary
2. Key Movements
3. Weekly Update
4. Leadership Insights
5. Risks \& Watchouts
6. Reporting Package
7. Promoting Package



Desired:

Leadership Email



added after

Risks \& Watchouts



Status: BACKLOG

