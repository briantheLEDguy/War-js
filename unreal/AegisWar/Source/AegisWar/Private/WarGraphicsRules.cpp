#include "WarGraphicsSettings.h"

FWarGraphicsSnapshot::FWarGraphicsSnapshot()
{
    Quality.SetFromSingleQualityLevel(0);
    Quality.ResolutionQuality = 75;
}

bool FWarGraphicsSnapshot::operator==(const FWarGraphicsSnapshot& Other) const
{
    return Mode == Other.Mode && Resolution == Other.Resolution && Quality == Other.Quality
        && FrameLimit == Other.FrameLimit && bVSync == Other.bVSync;
}

void WarGraphics::SetPreset(FWarGraphicsSnapshot& Value, int32 Level)
{
    const float Scale = Value.Quality.ResolutionQuality;
    Value.Quality.SetFromSingleQualityLevel(FMath::Clamp(Level, 0, 3));
    Value.Quality.ResolutionQuality = Scale;
}

int32 WarGraphics::Preset(const FWarGraphicsSnapshot& Value)
{
    for (int32 Level = 0; Level < 4; ++Level)
    {
        auto Test = Value;
        SetPreset(Test, Level);
        if (Test.Quality == Value.Quality) return Level;
    }
    return -1;
}

void WarGraphics::Sanitize(FWarGraphicsSnapshot& V, float MinScale, float MaxScale)
{
    if (V.Mode != EWindowMode::Windowed && V.Mode != EWindowMode::WindowedFullscreen && V.Mode != EWindowMode::Fullscreen)
        V.Mode = EWindowMode::Windowed;
    if (V.Resolution.X <= 0 || V.Resolution.Y <= 0 || V.Resolution.X > 32768 || V.Resolution.Y > 32768)
        V.Resolution = FIntPoint(1280, 720);
    V.FrameLimit = FMath::IsFinite(V.FrameLimit) ? FMath::Clamp(V.FrameLimit, 30.f, 240.f) : 60.f;
    const float Low = FMath::Clamp(FMath::IsFinite(MinScale) ? MinScale : 50.f, 50.f, 100.f);
    const float High = FMath::Clamp(FMath::IsFinite(MaxScale) ? MaxScale : 100.f, Low, 100.f);
    V.Quality.ResolutionQuality = FMath::Clamp(FMath::IsFinite(V.Quality.ResolutionQuality) ? V.Quality.ResolutionQuality : 75.f, Low, High);
    for (int32* Level : {&V.Quality.ViewDistanceQuality, &V.Quality.AntiAliasingQuality, &V.Quality.ShadowQuality,
        &V.Quality.GlobalIlluminationQuality, &V.Quality.ReflectionQuality, &V.Quality.PostProcessQuality,
        &V.Quality.TextureQuality, &V.Quality.EffectsQuality, &V.Quality.FoliageQuality, &V.Quality.ShadingQuality,
        &V.Quality.LandscapeQuality}) *Level = FMath::Clamp(*Level, 0, 3);
}

void WarGraphics::FilterResolutions(TArray<FIntPoint>& Values, FIntPoint Maximum)
{
    Values.RemoveAll([Maximum](FIntPoint P) { return P.X <= 0 || P.Y <= 0 || P.X > Maximum.X || P.Y > Maximum.Y; });
    Values.Sort([](FIntPoint A, FIntPoint B) { return A.X == B.X ? A.Y < B.Y : A.X < B.X; });
    for (int32 I = Values.Num() - 1; I > 0; --I) if (Values[I] == Values[I - 1]) Values.RemoveAt(I);
}

bool WarGraphics::Validate(const FWarGraphicsSnapshot& V, const FWarGraphicsSnapshot& Applied,
    const FWarGraphicsCapabilities& C, FString& Error)
{
    auto Safe = V;
    Sanitize(Safe, C.MinScale, C.MaxScale);
    if (!(Safe == V)) { Error = TEXT("Invalid graphics value. Restore defaults or choose a supported value."); return false; }
    if (!C.bCanRender) { Error = TEXT("Graphics settings require a rendered game window."); return false; }
    const bool Changed = V.Mode != Applied.Mode || V.Resolution != Applied.Resolution;
    if (Changed && !C.bCanChangeDisplay) { Error = C.Notice; return false; }
    if (!Changed) return true; // Enumeration failure must not invalidate the working mode.
    const bool Supported = V.Mode == EWindowMode::WindowedFullscreen ? V.Resolution == C.Desktop
        : V.Mode == EWindowMode::Fullscreen ? C.bFullscreen && C.FullscreenResolutions.Contains(V.Resolution)
        : C.WindowedResolutions.Contains(V.Resolution);
    if (!Supported) { Error = TEXT("That display mode is no longer available. Choose an available resolution."); return false; }
    return true;
}

FIntPoint WarGraphics::PickResolution(FIntPoint Current, const TArray<FIntPoint>& Options)
{
    if (Options.Contains(Current) || Options.IsEmpty()) return Current;
    // Switching modes must not silently jump to the largest (possibly supersampled) mode.
    FIntPoint Best = Options[0];
    for (const auto Candidate : Options)
        if (int64(Candidate.X) * Candidate.Y < int64(Best.X) * Best.Y) Best = Candidate;
    for (const auto Candidate : Options)
        if (Candidate.X <= Current.X && Candidate.Y <= Current.Y
            && int64(Candidate.X) * Candidate.Y > int64(Best.X) * Best.Y) Best = Candidate;
    return Best;
}

FWarGraphicsSnapshot WarGraphics::Recovery(const FWarGraphicsSnapshot& V, const FWarGraphicsCapabilities& C)
{
    auto Safe = V;
    Sanitize(Safe, C.MinScale, C.MaxScale);
    const bool Supported = Safe.Mode == EWindowMode::WindowedFullscreen ? Safe.Resolution == C.Desktop
        : Safe.Mode == EWindowMode::Fullscreen ? C.bFullscreen && C.FullscreenResolutions.Contains(Safe.Resolution)
        : Safe.Resolution.X <= C.WorkArea.X && Safe.Resolution.Y <= C.WorkArea.Y;
    if (!Supported && C.WorkArea.X > 0 && C.WorkArea.Y > 0)
    {
        Safe.Mode = EWindowMode::Windowed;
        Safe.Resolution = FIntPoint(FMath::Min(1280, C.WorkArea.X), FMath::Min(720, C.WorkArea.Y));
    }
    return Safe;
}
