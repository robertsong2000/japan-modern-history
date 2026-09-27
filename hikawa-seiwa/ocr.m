#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <AppKit/AppKit.h>
#import <ImageIO/ImageIO.h>
#import <CoreGraphics/CoreGraphics.h>

static CGImageRef rotateCCW(CGImageRef image) {
    size_t w = CGImageGetWidth(image);
    size_t h = CGImageGetHeight(image);
    CGColorSpaceRef cs = CGColorSpaceCreateDeviceRGB();
    CGContextRef ctx = CGBitmapContextCreate(NULL, h, w, 8, 0, cs, kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);
    CGColorSpaceRelease(cs);
    if (!ctx) return NULL;
    CGContextTranslateCTM(ctx, h, 0);
    CGContextRotateCTM(ctx, M_PI_2);
    CGContextDrawImage(ctx, CGRectMake(0, 0, w, h), image);
    CGImageRef rotated = CGBitmapContextCreateImage(ctx);
    CGContextRelease(ctx);
    return rotated;
}

static NSString *readingOrder(NSArray<VNRecognizedTextObservation *> *observations) {
    NSMutableArray<NSDictionary *> *lines = [NSMutableArray array];
    for (VNRecognizedTextObservation *obs in observations) {
        VNRecognizedText *top = [[obs topCandidates:1] firstObject];
        if (!top) continue;
        NSString *text = [top.string stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
        if (text.length == 0) continue;
        CGRect box = obs.boundingBox;
        [lines addObject:@{
            @"text": text,
            @"x": @(CGRectGetMidX(box)),
            @"y": @(CGRectGetMaxY(box))
        }];
    }
    [lines sortUsingComparator:^NSComparisonResult(NSDictionary *a, NSDictionary *b) {
        return [b[@"y"] compare:a[@"y"]];
    }];
    NSMutableArray<NSMutableArray *> *rows = [NSMutableArray array];
    const double gap = 0.012;
    for (NSDictionary *line in lines) {
        NSMutableArray *last = rows.lastObject;
        if (last && fabs([line[@"y"] doubleValue] - [last[0][@"y"] doubleValue]) < gap) {
            [last addObject:line];
        } else {
            [rows addObject:[NSMutableArray arrayWithObject:line]];
        }
    }
    NSMutableArray<NSString *> *parts = [NSMutableArray array];
    for (NSMutableArray *row in rows) {
        [row sortUsingComparator:^NSComparisonResult(NSDictionary *a, NSDictionary *b) {
            return [a[@"x"] compare:b[@"x"]];
        }];
        NSMutableString *joined = [NSMutableString string];
        for (NSDictionary *line in row) {
            [joined appendString:line[@"text"]];
        }
        [parts addObject:joined];
    }
    return [parts componentsJoinedByString:@"\n"];
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 2) return 1;
        BOOL rotate = YES;
        int argi = 1;
        if (argc > 1 && strcmp(argv[1], "--flat") == 0) {
            rotate = NO;
            argi = 2;
        }
        if (argc <= argi) return 1;
        NSString *path = [NSString stringWithUTF8String:argv[argi]];
        NSURL *url = [NSURL fileURLWithPath:path];
        CGImageSourceRef source = CGImageSourceCreateWithURL((__bridge CFURLRef)url, NULL);
        if (!source) return 2;
        CGImageRef image = CGImageSourceCreateImageAtIndex(source, 0, NULL);
        CFRelease(source);
        CGImageRef rotated = NULL;
        if (rotate) {
            rotated = rotateCCW(image);
            CGImageRelease(image);
            if (!rotated) return 3;
        } else {
            rotated = image;
        }
        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        request.recognitionLanguages = @[@"ja-JP"];
        request.usesLanguageCorrection = YES;
        request.minimumTextHeight = 0.0;
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:rotated options:@{}];
        CGImageRelease(rotated);
        NSError *error = nil;
        if (![handler performRequests:@[request] error:&error]) {
            fprintf(stderr, "%s\n", error.localizedDescription.UTF8String);
            return 2;
        }
        fprintf(stderr, "observations %lu\n", (unsigned long)request.results.count);
        NSString *text = readingOrder(request.results);
        printf("%s\n", text.UTF8String);
    }
    return 0;
}
