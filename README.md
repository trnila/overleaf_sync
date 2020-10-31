# overleaf_sync
Sync your projects from overleaf to git repository.

```sh
$ cat > ~/.overleaf
[auth]
email = YOUR_EMAIL
password = YOUR_PASSWORD

$ ./overleaf_sync.py sync_all ~/overleaf
$ ./overleaf_sync.py sync ~/overleaf/project_1
```
