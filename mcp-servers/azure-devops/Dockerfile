# Use an official Node.js runtime as a parent image
FROM node:20-slim

WORKDIR /usr/src/app

# Copy the entrypoint script and make it executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# The command to run the server, which will be passed to the entrypoint script
CMD ["npx", "-y", "@wangkanai/devops-mcp"]
