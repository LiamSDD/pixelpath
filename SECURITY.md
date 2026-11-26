# Security Policy

pixelpath parses untrusted SVG documents, so it treats parser and resource
exhaustion bugs as security issues.

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| < 0.2 | No |

Fixes are released as a new patch version of the latest supported minor release.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately through GitHub's
[private vulnerability reporting](https://github.com/LiamSDD/pixelpath/security/advisories/new)
(the **Security** tab of the repository, then **Report a vulnerability**).

Include, where possible:

- the smallest SVG file or input that triggers the problem;
- the exact command or Python call you ran, and the pixelpath and Python versions;
- what happened (traceback, memory use, run time) and what you expected.

You should receive an acknowledgement within a few days. Once the issue is
confirmed, a fix and a GitHub security advisory will be prepared together, and
you will be credited unless you prefer otherwise.

## Scope

In scope:

- **XML entity attacks**: XXE (external entity) file disclosure, "billion laughs"
  and other entity-expansion attacks, or any way to get a `<!DOCTYPE>` or
  `<!ENTITY>` declaration past the refusal check.
- **Resource exhaustion from crafted input**: paths, curves, arcs, transforms or
  references that cause excessive CPU time or memory use, and huge declared
  dimensions or size options that bypass the output size limits
  (16384 pixels per side, 100 megapixels in total).
- **Crashes on malformed input**: any input that makes `render_svg` or the
  `pixelpath` command fail with something other than `SVGError` (or its subclass
  `UnsafeSVGError`), `ValueError`, or a clean error message and exit status `1`,
  such as an unhandled exception, a hang or an interpreter crash.

Out of scope:

- Incorrect rendering of valid SVG that has no security impact; please open a
  regular bug report instead.
- Resource use that is proportional to legitimately requested output, for
  example rendering a very large but within-limit image.
- Vulnerabilities in Python itself or in the standard library; please report
  those to the [Python Security Response Team](https://www.python.org/dev/security/).
