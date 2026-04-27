# hfdl-recorder

A sigmond-compliant HFDL (High Frequency Data Link) recorder for
[ka9q-radio](https://github.com/ka9q/ka9q-radio).

`hfdl-recorder` subscribes to per-band IQ multicast streams from one or
more `radiod` instances via [ka9q-python](https://github.com/ka9q/ka9q-python),
supervises one [`dumphfdl`](https://github.com/szpajder/dumphfdl) subprocess
per enabled band (feeding it CS16 IQ via stdin), and writes the decoded
JSON to a local file per band — optionally pushing to
`feed.airframes.io:5556` over TCP.

It is the fourth client in the HamSCI sigmond contract v0.4 family,
following the same Pattern A install layout and deploy ergonomics as
[psk-recorder](https://github.com/mijahauan/psk-recorder),
[wspr-recorder](https://github.com/mijahauan/wspr-recorder), and
[hf-timestd](https://github.com/mijahauan/hf-timestd).

## Quick start

```bash
# First-run install (creates user, venv, builds dumphfdl, installs systemd unit)
sudo ./scripts/install.sh

# Edit /etc/hfdl-recorder/hfdl-recorder-config.toml — set station_id,
# radiod_status mDNS hostname, and which bands to enable.

# Validate the config
sudo -u hfdlrec hfdl-recorder validate --json

# Start it
sudo systemctl start hfdl-recorder@my-rx888
```

## Documentation

- See [CLAUDE.md](CLAUDE.md) for development briefing and architecture.
- See [config/hfdl-recorder-config.toml.template](config/hfdl-recorder-config.toml.template)
  for the full config schema.
- The client contract v0.4 spec lives in
  [sigmond/docs/CLIENT-CONTRACT.md](https://github.com/mijahauan/sigmond/blob/main/docs/CLIENT-CONTRACT.md).

## License

MIT — see [LICENSE](LICENSE).
