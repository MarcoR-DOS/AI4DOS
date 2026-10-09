#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p client/build
cc -std=c89 -Wall -Wextra -Werror -Iclient/include client/src/main.c client/src/charset.c client/src/config.c client/src/l10n.c client/src/protocol.c client/src/sha256.c tests/native_transport.c -o client/build/ai4dos-host
cc -std=c89 -Wall -Wextra -Werror -Iclient/include client/tests/coretest.c client/src/protocol.c client/src/sha256.c -o client/build/coretest-host
client/build/coretest-host
cc -std=c89 -Wall -Wextra -Werror -Iclient/include client/tests/uitest.c client/src/video.c client/src/editor.c client/src/glyphs.c client/src/controls.c client/src/l10n.c client/src/config.c client/src/transcr.c client/src/chatfile.c -o client/build/uitest-host
client/build/uitest-host
cc -std=c89 -Wall -Wextra -Werror -Iclient/include client/tests/tstest.c client/src/ui.c client/src/video.c client/src/editor.c client/src/glyphs.c client/src/controls.c client/src/l10n.c client/src/transcr.c client/src/chatfile.c -o client/build/tstest-host
(cd client/build && ./tstest-host)

cc -std=c89 -Wall -Wextra -Werror -Iclient/include client/tests/nettest.c client/src/network.c -o client/build/nettest-host
client/build/nettest-host

cc -std=c89 -Wall -Wextra -Werror -Iclient/include client/tests/chartest.c client/src/charset.c -o client/build/charsettest-host
client/build/charsettest-host

cc -std=c89 -Wall -Wextra -Werror -Iclient/include client/tests/systest.c client/src/video.c client/src/editor.c client/src/glyphs.c client/src/controls.c client/src/l10n.c client/src/transcr.c client/src/chatfile.c client/src/config.c client/src/charset.c client/src/protocol.c client/src/sha256.c -o client/build/systest-host
(cd client/build && ./systest-host)
