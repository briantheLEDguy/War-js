#pragma once

#include "CoreMinimal.h"

class FJsonObject;
class FRenderTarget;
class UWorld;

// Public view readback only. The caller must independently bind the screenshot frame.
namespace WarCitadelLumenViewProbe
{
    /** Reads the calling thread's CVar value, including reference and float CVars. */
    TSharedPtr<FJsonObject> ReadConsoleVariable(const TCHAR* Name);
    bool Arm(UWorld* World, const FRenderTarget* GameRenderTarget, const FString& Nonce);
    TSharedPtr<FJsonObject> FindFrame(const FString& Nonce, uint32 ImageFrameNumber);
    /** Unbound view-window diagnostic; cannot certify the screenshot's frame. */
    TSharedPtr<FJsonObject> LatestUnbound(const FString& Nonce);
    void Disarm();
}
