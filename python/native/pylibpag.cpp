#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <limits>
#include <memory>
#include <new>
#include <string>
#include <utility>
#include <vector>
#include "pag/file.h"

#if defined(_WIN32)
#define PYLIBPAG_API __declspec(dllexport)
#else
#define PYLIBPAG_API __attribute__((visibility("default")))
#endif

struct PylibpagBytes {
  const uint8_t* data;
  size_t size;
};

namespace {
thread_local std::string lastError;

int Fail(int status, std::string message) {
  lastError = std::move(message);
  return status;
}

pag::ByteData* CopyBytes(const PylibpagBytes& source) {
  auto copy = pag::ByteData::MakeCopy(source.data, source.size);
  if (copy == nullptr || copy->length() != source.size) {
    throw std::bad_alloc();
  }
  return copy.release();
}

std::shared_ptr<pag::File> MakeFile(const PylibpagBytes* frames, size_t frameCount, int32_t width,
                                    int32_t height, float frameRate, const PylibpagBytes* audio,
                                    int64_t audioStartFrame) {
  auto composition = std::make_unique<pag::BitmapComposition>();
  composition->width = width;
  composition->height = height;
  composition->duration = static_cast<pag::Frame>(frameCount);
  composition->frameRate = frameRate;

  if (audio != nullptr) {
    composition->audioBytes = CopyBytes(*audio);
    composition->audioStartTime = audioStartFrame;
  }

  auto sequence = std::make_unique<pag::BitmapSequence>();
  sequence->composition = composition.get();
  sequence->width = width;
  sequence->height = height;
  sequence->frameRate = frameRate;
  auto* sequencePointer = sequence.get();
  composition->sequences.push_back(sequence.get());
  sequence.release();

  for (size_t index = 0; index < frameCount; ++index) {
    auto frame = std::make_unique<pag::BitmapFrame>();
    frame->isKeyframe = true;

    auto bitmap = std::make_unique<pag::BitmapRect>();
    bitmap->fileBytes = CopyBytes(frames[index]);
    frame->bitmaps.push_back(bitmap.get());
    bitmap.release();
    sequencePointer->frames.push_back(frame.get());
    frame.release();
  }

  std::vector<pag::Composition*> compositions = {composition.get()};
  composition.release();
  return pag::Codec::VerifyAndMake(compositions, {});
}
}  // namespace

extern "C" {
PYLIBPAG_API int pylibpag_encode_webp_frames(const PylibpagBytes* frames, size_t frameCount,
                                             int32_t width, int32_t height, float frameRate,
                                             const uint8_t* audioData, size_t audioSize,
                                             int64_t audioStartFrame, uint8_t** outputData,
                                             size_t* outputSize) {
  if (outputData == nullptr || outputSize == nullptr) {
    return Fail(1, "Output pointers must not be null");
  }
  *outputData = nullptr;
  *outputSize = 0;
  lastError.clear();

  if (frames == nullptr || frameCount == 0) {
    return Fail(1, "At least one WebP frame is required");
  }
  if (frameCount > static_cast<size_t>(std::numeric_limits<int64_t>::max())) {
    return Fail(1, "Frame count is too large");
  }
  if (width <= 0 || height <= 0) {
    return Fail(1, "Width and height must be positive");
  }
  if (!std::isfinite(frameRate) || frameRate <= 0) {
    return Fail(1, "Frame rate must be finite and positive");
  }
  for (size_t index = 0; index < frameCount; ++index) {
    if (frames[index].data == nullptr || frames[index].size == 0) {
      return Fail(1, "WebP frames must not be empty");
    }
  }
  if ((audioData == nullptr) != (audioSize == 0)) {
    return Fail(1, "Audio data and size must either both be present or both be absent");
  }

  try {
    PylibpagBytes audio = {audioData, audioSize};
    auto file = MakeFile(frames, frameCount, width, height, frameRate,
                         audioData == nullptr ? nullptr : &audio, audioStartFrame);
    if (file == nullptr) {
      return Fail(2, "libpag rejected the bitmap composition");
    }

    auto encoded = pag::Codec::Encode(std::move(file));
    if (encoded == nullptr || encoded->length() == 0) {
      return Fail(3, "libpag failed to encode the PAG file");
    }

    auto* result = static_cast<uint8_t*>(std::malloc(encoded->length()));
    if (result == nullptr) {
      throw std::bad_alloc();
    }
    std::memcpy(result, encoded->data(), encoded->length());
    *outputData = result;
    *outputSize = encoded->length();
    return 0;
  } catch (const std::bad_alloc&) {
    return Fail(4, "Memory allocation failed");
  } catch (const std::exception& error) {
    return Fail(5, error.what());
  } catch (...) {
    return Fail(5, "Unknown native error");
  }
}

PYLIBPAG_API const char* pylibpag_last_error() {
  return lastError.c_str();
}

PYLIBPAG_API void pylibpag_free(void* pointer) {
  std::free(pointer);
}
}
