#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameUserSettings.h"
#include "Containers/Ticker.h"
#include "WarGraphicsSettings.generated.h"

struct FWarGraphicsSnapshot
{
    EWindowMode::Type Mode = EWindowMode::WindowedFullscreen;
    FIntPoint Resolution = FIntPoint(1280, 720);
    Scalability::FQualityLevels Quality;
    float FrameLimit = 60;
    bool bVSync = true;
    FWarGraphicsSnapshot();
    bool operator==(const FWarGraphicsSnapshot& Other) const;
};

struct FWarGraphicsCapabilities
{
    FIntPoint Desktop = FIntPoint::ZeroValue;
    FIntPoint WorkArea = FIntPoint::ZeroValue;
    TArray<FIntPoint> FullscreenResolutions;
    TArray<FIntPoint> WindowedResolutions;
    float MinScale = 50;
    float MaxScale = 100;
    bool bCanRender = false;
    bool bCanChangeDisplay = false;
    bool bFullscreen = false;
    FString Notice;
};

namespace WarGraphics
{
    AEGISWAR_API void Sanitize(FWarGraphicsSnapshot& Value, float MinScale = 50, float MaxScale = 100);
    AEGISWAR_API void SetPreset(FWarGraphicsSnapshot& Value, int32 Level);
    AEGISWAR_API int32 Preset(const FWarGraphicsSnapshot& Value);
    AEGISWAR_API void FilterResolutions(TArray<FIntPoint>& Values, FIntPoint Maximum);
    AEGISWAR_API FIntPoint PickResolution(FIntPoint Current, const TArray<FIntPoint>& Options);
    AEGISWAR_API bool Validate(const FWarGraphicsSnapshot& Value, const FWarGraphicsSnapshot& Applied,
        const FWarGraphicsCapabilities& Caps, FString& Error);
    AEGISWAR_API FWarGraphicsSnapshot Recovery(const FWarGraphicsSnapshot& Value, const FWarGraphicsCapabilities& Caps);
}

/** Client-only transaction owner. The core ticker outlives menus and does not use world time. */
UCLASS(Config=GameUserSettings)
class AEGISWAR_API UWarGraphicsSettings : public UGameUserSettings
{
    GENERATED_BODY()
public:
    virtual void SetToDefaults() override;
    virtual void LoadSettings(bool bForceReload = false) override;
    virtual void ValidateSettings() override;
    virtual void SaveSettings() override;
    virtual void ConfirmVideoMode() override;
    virtual void BeginDestroy() override;

    static UWarGraphicsSettings* Get();
    FWarGraphicsCapabilities Capabilities() const;
    FWarGraphicsSnapshot Capture() const;
    FWarGraphicsSnapshot Actual() const;
    void BeginEditing();
    void RestoreDraftDefaults();
    bool Preview();
    bool Keep();
    void Revert(const FString& Reason = TEXT("Changes reverted."));
    void EndEditing();
    bool IsPreviewing() const { return bPreviewing; }
    bool IsRecovering() const { return bRecovering; }
    bool CanKeep() const { return bPreviewing && bDisplayVerified; }
    int32 SecondsRemaining() const;
    const FString& GetMessage() const { return Message; }
    const FWarGraphicsSnapshot& GetApplied() const { return Applied; }
    FWarGraphicsSnapshot Draft;

private:
    friend class FWarGraphicsTransactionTest;
    void Write(const FWarGraphicsSnapshot& Value);
    void ApplySnapshot(const FWarGraphicsSnapshot& Value, bool bDisplay);
    bool TickPreview(float DeltaTime);
    void OnActivation(bool bActive);
    void StopPreview();
    FWarGraphicsSnapshot Applied;
    FWarGraphicsSnapshot Confirmed;
    bool bPreviewing = false;
    bool bRecovering = false;
    bool bRecoveryFallback = false;
    bool bDisplayVerified = false;
    bool bLastSaveSucceeded = false;
    double Deadline = 0;
    double VerifyAfter = 0;
    int32 ConfirmedPreferredMode = 1;
    FString Message;
    FTSTicker::FDelegateHandle TickerHandle;
    FDelegateHandle ActivationHandle;
};
