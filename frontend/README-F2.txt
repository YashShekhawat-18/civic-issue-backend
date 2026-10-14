FRONTEND PHASE F2 - Report an issue (map + photo + duplicate warning)
Needs F1 already in your frontend folder.

Install (PowerShell). Change the first path if your frontend folder is elsewhere:
    cd "D:\iot\civic issuse\civic-issue-backend\frontend"
    Expand-Archive "D:\Download\civic-frontend-F2.zip" -DestinationPath . -Force
    Copy-Item -Recurse -Force civic-frontend-F2\* .
    Remove-Item -Recurse -Force civic-frontend-F2
    npm install
    npm run dev

Then log in as a citizen -> "Report issue".
The backend must be running on port 8000.
