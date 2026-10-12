/* keystate <name> <keycode> [wait_ms]: exit 0 if the key is held on the input device named <name> */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/input.h>
static int find(const char *want, char *out) {
  for (int i = 0; i < 32; i++) {
    char p[64], n[128] = {0};
    snprintf(p, sizeof p, "/dev/input/event%d", i);
    int fd = open(p, O_RDONLY);
    if (fd < 0) continue;
    if (ioctl(fd, EVIOCGNAME(sizeof n - 1), n) >= 0 && !strcmp(n, want)) { strcpy(out, p); close(fd); return 1; }
    close(fd);
  }
  return 0;
}
int main(int c, char **v) {
  if (c < 3) return 2;
  int code = atoi(v[2]), wait = c > 3 ? atoi(v[3]) : 0, t = 0;
  char path[64];
  while (!find(v[1], path)) { if (t >= wait) return 3; usleep(100000); t += 100; }
  int fd = open(path, O_RDONLY);
  if (fd < 0) return 4;
  unsigned char k[KEY_MAX / 8 + 1];
  memset(k, 0, sizeof k);
  if (ioctl(fd, EVIOCGKEY(sizeof k), k) < 0) return 5;
  return (k[code / 8] >> (code % 8)) & 1 ? 0 : 1;
}
