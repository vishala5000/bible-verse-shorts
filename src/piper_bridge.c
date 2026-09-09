#include <piper.h>

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#ifdef __ANDROID__
#include <android/log.h>
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, "PiperBridge", __VA_ARGS__)
#else
#define LOGE(...) fprintf(stderr, __VA_ARGS__)
#endif


static int write_wav_header(
    FILE *file,
    uint32_t sample_rate,
    uint32_t sample_count
) {
    uint16_t audio_format = 3; /* IEEE float */
    uint16_t channels = 1;
    uint16_t bits_per_sample = 32;

    uint32_t byte_rate =
        sample_rate * channels * sizeof(float);

    uint16_t block_align =
        channels * sizeof(float);

    uint32_t data_size =
        sample_count * sizeof(float);

    uint32_t riff_size =
        36 + data_size;

    fwrite("RIFF", 1, 4, file);
    fwrite(&riff_size, 4, 1, file);
    fwrite("WAVE", 1, 4, file);

    fwrite("fmt ", 1, 4, file);

    uint32_t fmt_size = 16;
    fwrite(&fmt_size, 4, 1, file);

    fwrite(&audio_format, 2, 1, file);
    fwrite(&channels, 2, 1, file);
    fwrite(&sample_rate, 4, 1, file);
    fwrite(&byte_rate, 4, 1, file);
    fwrite(&block_align, 2, 1, file);
    fwrite(&bits_per_sample, 2, 1, file);

    fwrite("data", 1, 4, file);
    fwrite(&data_size, 4, 1, file);

    return 0;
}


/*
 * Synthesize directly to a 32-bit float WAV.
 *
 * Returns:
 *   0  success
 *  <0 error
 */
int piper_bridge_synthesize(
    const char *model_path,
    const char *config_path,
    const char *espeak_data_path,
    const char *text,
    const char *wav_path
) {
    if (
        !model_path ||
        !config_path ||
        !espeak_data_path ||
        !text ||
        !wav_path
    ) {
        return -10;
    }

    piper_synthesizer *synth =
        piper_create(
            model_path,
            config_path,
            espeak_data_path
        );

    if (!synth) {
        LOGE("piper_create failed");
        return -20;
    }

    piper_synthesize_options options =
        piper_default_synthesize_options(
            synth
        );

    int result =
        piper_synthesize_start(
            synth,
            text,
            &options
        );

    if (result != PIPER_OK) {
        LOGE(
            "piper_synthesize_start failed: %d",
            result
        );

        piper_free(synth);
        return -30;
    }

    FILE *file =
        fopen(
            wav_path,
            "wb"
        );

    if (!file) {
        piper_free(synth);
        return -40;
    }

    /*
     * We don't know the final sample count before synthesis.
     *
     * Write a placeholder WAV header first and patch it after
     * synthesis is complete.
     */
    write_wav_header(
        file,
        22050,
        0
    );

    uint32_t total_samples = 0;
    uint32_t sample_rate = 22050;

    piper_audio_chunk chunk;

    while (1) {
        memset(
            &chunk,
            0,
            sizeof(chunk)
        );

        result =
            piper_synthesize_next(
                synth,
                &chunk
            );

        if (result == PIPER_ERR_GENERIC) {
            fclose(file);
            piper_free(synth);
            return -50;
        }

        if (chunk.samples &&
            chunk.num_samples > 0) {

            fwrite(
                chunk.samples,
                sizeof(float),
                chunk.num_samples,
                file
            );

            total_samples +=
                (uint32_t)chunk.num_samples;
        }

        if (result == PIPER_DONE) {
            break;
        }
    }

    fflush(file);

    fseek(
        file,
        0,
        SEEK_SET
    );

    write_wav_header(
        file,
        sample_rate,
        total_samples
    );

    fclose(file);

    piper_free(synth);

    return 0;
}
