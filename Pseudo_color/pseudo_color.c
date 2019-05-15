#include <stdio.h>
#include <stdlib.h>

#pragma pack(push,1)
/* Windows 3.x bitmap file header */
typedef struct {
    char         filetype[2];   /* magic - always 'B' 'M' */
    unsigned int filesize;
    short        reserved1;
    short        reserved2;
    unsigned int dataoffset;    /* offset in bytes to actual bitmap data */
} file_header;

/* Windows 3.x bitmap full header, including file header */
typedef struct {
    file_header  fileheader;
    unsigned int headersize;
    int          width;
    int          height;
    short        planes;
    short        bitsperpixel;  /* we only support the value 24 here */
    unsigned int compression;   /* we do not support compression */
    unsigned int bitmapsize;
    int          horizontalres;
    int          verticalres;
    unsigned int numcolors;
    unsigned int importantcolors;
} bitmap_header;

typedef struct {
    unsigned char b;
    unsigned char g;
    unsigned char r;
} pixel;
#pragma pack(pop)

typedef struct {
    int b;
    int g;
    int r;
} rgb_operation;

pixel colormapJet(unsigned char gray);
void pseudoColor(char *data, int height, int width, int bitsperpixel, rgb_operation op);

int processImage(char* input, char *output, rgb_operation RGB_operation) {

    FILE *fp,*out;
    bitmap_header* hp;
    char *data;
    char *header;

    // Open input file:
    fp = fopen(input, "rb");

    // Read the input file headers:
    hp = (bitmap_header*)malloc(sizeof(bitmap_header));
    fread(hp, sizeof(bitmap_header), 1, fp);

    printf("dataoffset: %d\n", hp->fileheader.dataoffset);
    printf("height: %d\n", hp->height);
    printf("width: %d\n", hp->width);
    printf("bits per pixel: %d\n", hp->bitsperpixel);

    // Read the entire header
    header = (char*)malloc(sizeof(char)*hp->fileheader.dataoffset);
    fseek(fp, 0, SEEK_SET);
    fread(header, sizeof(char),hp->fileheader.dataoffset, fp);

    // Read the data of the image:
    data = (char*)malloc(sizeof(char)*hp->bitmapsize);
    fseek(fp,sizeof(char)*hp->fileheader.dataoffset,SEEK_SET);
    fread(data,sizeof(char),hp->bitmapsize, fp);
    printf("Image loaded\n");

    // Open output file:
    out = fopen(output, "wb+");

    // Write header info
    // fwrite(hp,sizeof(char),sizeof(bitmap_header),out);
    fwrite(header, sizeof(char), hp->fileheader.dataoffset, out);

    fseek(out,sizeof(char)*hp->fileheader.dataoffset,SEEK_SET);

    pseudoColor(data, hp->height, hp->width, hp->bitsperpixel, RGB_operation);

    // Write output file:
    fwrite(data,sizeof(char),hp->bitmapsize,out);
    printf("Image processed\n");

    fclose(fp);
    fclose(out);
    free(hp);
    free(data);
    free(header);
    return 0;
}

pixel colormapJet(unsigned char gray){
  pixel color;
  // divide 255 range in 4 ramps of RGB
  if (gray < 32){   //blue half ramp
    color.r = 0;
    color.g = 0;
    color.b = 128 + (gray * 4);
  } else {
    if (gray < (32+64)) {   //green ramp
      color.r = 0;
      color.b = 255;
      color.g = (gray - 32) * 4;
    } else {
      if (gray < (32+128)) {  // blue-red ramp
        color.g = 255;
        color.r = (gray-(32+64)) * 4;
        color.b = 255- ((gray-(32+64)) * 4);
      } else {
        if (gray < (32+64+128)){   // green ramp
          color.r = 255;
          color.b = 0;
          color.g = 255 - ((gray-(128+32)) * 4);
        } else {  //red half ramp
          color.g = 0;
          color.b = 0;
          color.r = 255 - ((gray-(128+64+32)) * 4);
        }
      }
    }
  }
  return color;
}

void pseudoColor(char *data, int height, int width, int bitsperpixel, rgb_operation op) {
  int bytesperpixel = bitsperpixel/8;
  printf("bytes per pixel: %d\n", bytesperpixel);
  for (int i = 0; i < height; i++)
  {
    for (int j = 0; j < width * bytesperpixel; j += bytesperpixel)
    {
      int index = (i * width * bytesperpixel) + (j);
      // pixel pixel = colormapJet(data[index + 2]);
      // pixel pixel = colormapJet(
        // data[index + 0] + data[index + 1] - data[index + 2] );
      pixel pixel = colormapJet((unsigned char)(op.b*(int)data[index + 0]) + (op.g*(int)data[index + 1]) + (op.r*(int)data[index + 2]) );
      data[index + 2] = pixel.r;
      data[index + 1] = pixel.g;
      data[index + 0] = pixel.b;
    }
  }
}

int main(int argc, char *argv[]) {
    rgb_operation RGB_operation;
    RGB_operation.b = atoi(argv[5]);
    RGB_operation.g = atoi(argv[4]);
    RGB_operation.r = atoi(argv[3]);

    // printf("arguments R: %d, G: %d, B: %d\n", argv[5], argv[4], argv[3]);
    // printf("will process R: %d, G: %d, B: %d\n", RGB_operation.r, RGB_operation.g, RGB_operation.b);

    return processImage(argv[1], argv[2], RGB_operation);
}
