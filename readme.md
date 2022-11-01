# heart-beat
access some url and ping to heartbeat url.

## environment variable
- HB_CONFIG_PATH

## config example
```yaml
- url: http://some-domain.domain
  period: 10  # some integer value
  # cron: "*/15 * * * *"
  ping_url: http://healtchchecks.url
  headers:  # list: name, value pairs
    - name: Host
      value: hello.foo.bar
  params:
    - name: q
      value: xxx
  timeout:
    total: 180
    connect: 30
    sock_connect: 30
    sock_read: 120

```
