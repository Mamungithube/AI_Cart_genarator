FROM nginx:alpine

# Remove default configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configuration
COPY default.conf /etc/nginx/conf.d/

# Expose HTTP ports
EXPOSE 80 6000

CMD ["nginx", "-g", "daemon off;"]
