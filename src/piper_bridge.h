#ifndef PIPER_BRIDGE_H
#define PIPER_BRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

int piper_bridge_synthesize(
    const char *model_path,
    const char *config_path,
    const char *espeak_data_path,
    const char *text,
    const char *wav_path
);

#ifdef __cplusplus
}
#endif

#endif
