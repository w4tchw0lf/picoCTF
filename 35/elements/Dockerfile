FROM --platform=amd64 node:21-bookworm-slim

ADD chrome.deb /tmp/chrome.deb
RUN apt-get update && \
	apt-get install -y /tmp/chrome.deb && \
	apt-get install -y xvfb && \
	rm -rf /var/lib/apt/lists/* /tmp/chrome.deb

WORKDIR /app

COPY flag.txt .
COPY index.mjs start_display.sh ./
COPY static ./static
COPY policy.json /etc/chromium/policies/managed/policy.json

CMD ./start_display.sh & DISPLAY=:99.0 su node -c "node index.mjs"
