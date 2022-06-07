# Starting the mock server

Inside the VM:

1. Navigate to `<repository_root>/_dev/license-retrival-mock-server`
2. Run `docker-compose up --build -d`
3. Change endpoints in `/etc/bildungslogin/config.ini` to
 
```
[APIEndpoint]
AuthServer = http://localhost:30000/auth
ResourceServer = http://localhost:30000/cr1
```

__NOTE__: `ResourceServer` can point either to `/cr1` or `/cr2` depending on the needs


## Accessing the documentation

After the server has been started you can access the swagger documentation under:

```
http://<vm_ip_address>:30000/docs
```

Where `<vm_ip_address>` is an external IP address of your VM 
_(the one you use to access Univention system)_


## Getting the licenses

The license package is taken from the 
`licenses/<cr_version>/<package_id>.json` file, where `<cr_version>` 
is either `cr1` or `cr2` and `<package_id>` is the ID sent in the request.
