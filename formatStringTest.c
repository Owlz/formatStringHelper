#include <stdio.h>

int loggedIn = 0;
char secret[] = "This is my super secret string!";

int main() {
  char f[512];
  
  printf("Input a format string: ");
  
  fgets(f, sizeof(f), stdin);

  printf(f);

  printf("\n");
  
  if (loggedIn) {
    printf("Yay! You logged in!\n");
  }
  else {
    printf("You aren't logged in :(\n");
  }

}

