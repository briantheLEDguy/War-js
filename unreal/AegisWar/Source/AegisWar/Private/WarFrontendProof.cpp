#include "WarFrontendProof.h"
#include "WarFrontendWidget.h"
#include "WarFrontendPresentation.h"
#include "EngineUtils.h"
#include "UObject/UObjectIterator.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMemory.h"
#include "HAL/PlatformMisc.h"
#include "UnrealClient.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ImageUtils.h"

namespace
{
    FString OutputFolder()
    {
        FString Run;
        FParse::Value(FCommandLine::Get(), TEXT("WarFrontendRun="), Run);
        FGuid Guid;
        return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("FrontendProof"),
            FGuid::Parse(Run, Guid) ? Guid.ToString(EGuidFormats::Digits) : TEXT("manual"));
    }
    bool CityHasDetail(UTextureRenderTarget2D* Target)
    {
        TArray<FColor> Pixels;
        if (!Target || !Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels) || Pixels.IsEmpty()) return false;
        TSet<uint32> Colors;
        for (const FColor& Pixel : Pixels)
            Colors.Add((uint32(Pixel.R >> 4) << 8) | (uint32(Pixel.G >> 4) << 4) | (Pixel.B >> 4));
        // A loaded render target can still be blank. This catches that regression;
        // screenshots still require inspection for actual models and framing.
        return Colors.Num() >= 16;
    }

}
bool UWarFrontendProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarFrontendProof"));
#endif
}
TStatId UWarFrontendProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarFrontendProof, STATGROUP_Tickables); }

void UWarFrontendProof::Finish(bool Passed, const FString& Detail)
{
    bFinished = true;
    IFileManager::Get().MakeDirectory(*OutputFolder(), true);
    auto Report = MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("passed"), Passed); Report->SetStringField(TEXT("detail"), Detail);
    Report->SetBoolField(TEXT("visualApproved"), false);
    Report->SetBoolField(TEXT("productionAdmission"), false);
    FrameTimes.Sort();
    Report->SetNumberField(TEXT("frames"), FrameTimes.Num());
    if (!FrameTimes.IsEmpty())
    {
        Report->SetNumberField(TEXT("medianFrameMs"), FrameTimes[FrameTimes.Num()/2]);
        Report->SetNumberField(TEXT("p95FrameMs"), FrameTimes[FMath::Min(FrameTimes.Num()-1, FMath::FloorToInt(FrameTimes.Num()*.95f))]);
    }
    Report->SetNumberField(TEXT("peakProcessMemoryMiB"), double(FPlatformMemory::GetStats().PeakUsedPhysical)/(1024*1024));
    const auto RecordFrames = [&Report](const TCHAR* Name, TArray<float>& Samples) {
        Samples.Sort();
        auto Stats = MakeShared<FJsonObject>(); Stats->SetNumberField(TEXT("frames"), Samples.Num());
        if (!Samples.IsEmpty())
        {
            Stats->SetNumberField(TEXT("medianMs"), Samples[Samples.Num()/2]);
            Stats->SetNumberField(TEXT("p95Ms"), Samples[FMath::Min(Samples.Num()-1, FMath::FloorToInt(Samples.Num()*.95f))]);
        }
        Report->SetObjectField(Name, Stats);
    };
    RecordFrames(TEXT("steady"), SteadyFrameTimes); RecordFrames(TEXT("crossfade"), FadeFrameTimes);
    Report->SetStringField(TEXT("timingScope"), TEXT("Whole game frame deltas with a 60 FPS cap; not isolated GPU cost"));
    FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json, *(OutputFolder()/TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}

void UWarFrontendProof::Tick(float Delta)
{
    if (bFinished) return;
    const double Now = FPlatformTime::Seconds();
    if (!Started) Started = Now;
    if (Now - Started > 240) { Finish(false, TEXT("Frontend fixture timed out")); return; }
    UWarFrontendWidget* Widget = nullptr;
    for (TObjectIterator<UWarFrontendWidget> It; It; ++It)
        if (It->GetWorld() == GetWorld() && It->IsInViewport()) { Widget = *It; break; }
    if (!Widget || !Widget->Presentation) return;
    auto* Presentation = Widget->Presentation.Get();
    if (Step > 0)
    {
        FrameTimes.Add(Delta * 1000);
        (Presentation->GetBlend() > 0 ? FadeFrameTimes : SteadyFrameTimes).Add(Delta * 1000);
    }
    if (Now < Next) return;
    if (AfterScreenshot)
    {
        auto Action = MoveTemp(AfterScreenshot); AfterScreenshot = nullptr;
        Action(Widget); Next = Now + 4; return;
    }
    IFileManager::Get().MakeDirectory(*OutputFolder(), true);
    const auto Screenshot = [](const TCHAR* Name) { FScreenshotRequest::RequestScreenshot(OutputFolder()/Name, true, false); };
    if (Step == 0)
    {
        if (Widget->Artwork.Num() != 3 || Widget->Artwork.Contains(nullptr))
        { Finish(false, TEXT("Logo, window or button artwork is not installed")); return; }
        if (!Presentation->GetCityTarget(0) || !Presentation->GetCityTarget(1)) return;
        if (Presentation->HasCharacter()) { Finish(false, TEXT("Initial login incorrectly displays a character")); return; }
        Next = Now + 5; ++Step; return;
    }
    if (Step == 1) { if (!CityHasDetail(Presentation->GetCityTarget(0))) { Finish(false, TEXT("Bastion city capture is empty")); return; } Screenshot(TEXT("login.png")); Next = Now + 1; ++Step; return; }
    if (Step == 2)
    {
        Presentation->SelectCharacter(TEXT("missing"), TEXT("missing"), TEXT("m"));
        Widget->CharacterName = TEXT("Mara Vell"); Widget->ShowCreation(); Next = Now + 5; ++Step; return;
    }
    if (Step == 3)
    {
        if (!Presentation->HasCharacter()) return;
        TArray<FColor> Pixels;
        auto* Target = Presentation->GetCharacterTarget();
        Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);
        int32 Covered = 0;
        for (auto& Pixel : Pixels) { if (Pixel.A < 128) ++Covered; Pixel.A = 255; }
        TArray64<uint8> Png;
        FImageUtils::PNGCompressImageArray(Target->SizeX, Target->SizeY, Pixels, Png);
        FFileHelper::SaveArrayToFile(Png, *(OutputFolder()/TEXT("character-raw.png")));
        UE_LOG(LogTemp, Display, TEXT("Frontend character capture occupied pixels: %d/%d"), Covered, Pixels.Num());
        if (Covered < Pixels.Num()/100 || Covered > Pixels.Num()*9/10)
        { Finish(false, TEXT("Character capture is empty or improperly framed")); return; }
        Screenshot(TEXT("prelate.png")); AfterScreenshot = [](auto* Frontend) { Frontend->ShowSelection(); }; Next = Now + .5; ++Step; return;
    }
    if (Step == 4)
    {
        Screenshot(TEXT("review.png")); AfterScreenshot = [](auto* Frontend) { Frontend->Presentation->Rotate(70); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 5)
    {
        Screenshot(TEXT("rotated.png"));
        AfterScreenshot = [](auto* Frontend) { Frontend->Career = TEXT("Sunfire Templar"); Frontend->ShowCreation(); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 6)
    {
        if (!Presentation->HasCharacter()) return;
        Screenshot(TEXT("templar.png")); AfterScreenshot = [](auto* Frontend) { Frontend->Career = TEXT("Ember Arcanist"); Frontend->ShowCreation(); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 7)
    {
        if (!Presentation->HasCharacter()) return;
        Screenshot(TEXT("arcanist.png")); AfterScreenshot = [](auto* Frontend) { Frontend->Race = TEXT("Greenskin"); Frontend->Career = TEXT("Warbrute"); Frontend->ShowCreation(); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 8)
    {
        if (!Presentation->HasCharacter()) return;
        Screenshot(TEXT("warbrute.png")); AfterScreenshot = [](auto* Frontend) { Frontend->ShowLogin(); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 9)
    {
        if (Presentation->GetActiveCity() != 1 || Presentation->GetBlend() > .01f) return;
        Screenshot(TEXT("riftspire.png")); AfterScreenshot = [](auto* Frontend) { Frontend->Presentation->SetReducedMotion(true); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 10)
    {
        if (!Presentation->HasCharacter() || !Presentation->IsReducedMotion()) { Finish(false, TEXT("Returning to login lost the draft")); return; }
        Screenshot(TEXT("reduced-motion.png")); AfterScreenshot = [](auto* Frontend) {
            Frontend->Presentation->SetReducedMotion(false);
            Frontend->Presentation->SelectCharacter(TEXT("missing"), TEXT("missing"), TEXT("m")); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 11)
    {
        if (Presentation->HasCharacter() || Presentation->GetCharacterStatus().IsEmpty()) { Finish(false, TEXT("Missing character did not fail recoverably")); return; }
        Screenshot(TEXT("missing-character.png")); AfterScreenshot = [](auto* Frontend) { Frontend->RefreshPreview(); };
        Next = Now + .5; ++Step; return;
    }
    if (Step == 12)
    {
        if (!Presentation->HasCharacter()) return;
        if (Presentation->GetBlend() < .35f || Presentation->GetBlend() > .65f) return;
        Screenshot(TEXT("crossfade.png")); Next = Now + 2; ++Step; return;
    }
    if (Step == 13)
    {
        Presentation->Shutdown();
        if (Presentation->HasCharacter() || Presentation->GetCityTarget(0) || Presentation->GetCharacterMaterial())
        { Finish(false, TEXT("Presentation resources survived shutdown")); return; }
        Finish(true, TEXT("Both cities, four exact character profiles, rotation, reduced motion, recoverable missing model and cleanup exercised"));
    }
}
