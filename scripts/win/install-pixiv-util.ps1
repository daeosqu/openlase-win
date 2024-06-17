Invoke-WebRequest -Uri "https://github.com/Nandaka/PixivUtil2/releases/download/v20230105/pixivutil202305.zip" -OutFile pixivutil202305.zip
Expand-Archive pixivutil202305.zip -DestinationPath "$HOME/.local/pixivutil" -Force
