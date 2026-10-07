#include "WarInterfaceProof.h"
#include "WarCitadelSiegeProof.h"
#include "WarWorldEditSubsystem.h"
#include "WarWorldEditWidget.h"
#include "WarWorldEditCatalog.h"
#include "WarWorldEditMap.h"
#include "WarInterfaceWidget.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarCityDefinition.h"
#include "WarCityNpc.h"
#include "WarZoneAnchor.h"
#include "WarZonePortal.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "EngineUtils.h"
#include "GameFramework/InputSettings.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectIterator.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"

namespace WarOrdinaryBuilderProofPrivate
{
    bool Fail(FString& Error, const FString& Detail) { Error = Detail; return false; }
    FString String(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name)
    { FString Value; if (Object) Object->TryGetStringField(Name, Value); return Value; }
    bool Equal(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, const FString& Value)
    { FString Actual; return Object && Object->TryGetStringField(Name, Actual) && Actual == Value; }
    bool Boolean(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, bool Expected)
    { bool Value; return Object && Object->TryGetBoolField(Name, Value) && Value == Expected; }
    bool Number(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, double Expected)
    { double Value; return Object && Object->TryGetNumberField(Name, Value) && Value == Expected; }
    bool Hex(const FString& Value, int32 Length)
    {
        if (Value.Len() != Length) return false;
        for (TCHAR C : Value) if (!((C >= TEXT('0') && C <= TEXT('9')) || (C >= TEXT('a') && C <= TEXT('f')))) return false;
        return true;
    }
    FString Absolute(FString Value)
    {
        Value = FPaths::ConvertRelativePathToFull(Value); FPaths::NormalizeFilename(Value);
        FPaths::CollapseRelativeDirectories(Value); return Value;
    }
    FString Identity(const FString& Value)
    {
        FString Result = Absolute(Value);
#if PLATFORM_WINDOWS
        Result = Result.ToLower();
#endif
        return Result;
    }
    bool AbsolutePath(const FString& Value)
    { return !Value.IsEmpty() && !FPaths::IsRelative(Value) && FPaths::IsSamePath(Value, Absolute(Value)); }
    bool PathEqual(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, const FString& Expected)
    { const FString Value = String(Object, Name); return AbsolutePath(Value) && FPaths::IsSamePath(Value, Expected); }
    bool Hash(const FString& Path, const FString& Expected, FString& Error)
    {
        FString Actual;
        if (!Hex(Expected, 64) || !WarCitadelProofHash::File(Path, Actual, Error) || Actual != Expected)
            return Fail(Error, TEXT("A bound file is missing or its raw bytes changed: ") + Path);
        return true;
    }
    TSharedPtr<FJsonObject> ReadJson(const FString& Path)
    {
        const int64 Size = IFileManager::Get().FileSize(*Path); FString Text; TSharedPtr<FJsonObject> Object;
        if (Size <= 0 || Size > 8000000 || !FFileHelper::LoadFileToString(Text, *Path)
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object)) return nullptr;
        return Object;
    }
    bool WriteNewJson(const FString& Path, const TSharedRef<FJsonObject>& Object, FString& Error)
    {
        // Proof evidence never replaces a previous receipt or an ordinary storage file.
        if (IFileManager::Get().FileExists(*Path)) return Fail(Error, TEXT("Preserve existing proof evidence: ") + Path);
        FString Text;
        if (!FJsonSerializer::Serialize(Object, TJsonWriterFactory<>::Create(&Text))
            || !FFileHelper::SaveStringToFile(Text, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
            return Fail(Error, TEXT("Could not write new proof evidence: ") + Path);
        return true;
    }
    bool Keys(const TSharedPtr<FJsonObject>& Object, const TArray<FString>& Expected)
    {
        if (!Object || Object->Values.Num() != Expected.Num()) return false;
        for (const FString& Name : Expected) if (!Object->HasField(Name)) return false;
        return true;
    }
    bool SameTable(const TSharedPtr<FJsonObject>& Left, const TSharedPtr<FJsonObject>& Right)
    {
        if (!Left || !Right || Left->Values.Num() != Right->Values.Num()) return false;
        for (const auto& Pair : Left->Values)
        { FString Value; if (!Pair.Value->TryGetString(Value) || !Equal(Right, *Pair.Key, Value)) return false; }
        return true;
    }
    bool SourceExtension(const FString& Extension)
    { return Extension == TEXT("cpp") || Extension == TEXT("h") || Extension == TEXT("hpp") || Extension == TEXT("inl") || Extension == TEXT("c") || Extension == TEXT("cs"); }
    bool BoundSource(const FString& Path)
    {
        const FString Extension = FPaths::GetExtension(Path).ToLower();
        const FString Project = Absolute(FPaths::ProjectDir()), Repository = Absolute(Project / TEXT("../.."));
        return (FPaths::IsUnderDirectory(Path, Project / TEXT("Source")) && SourceExtension(Extension))
            || (FPaths::IsUnderDirectory(Path, Project / TEXT("Config")) && Extension == TEXT("ini"))
            || (FPaths::IsUnderDirectory(Path, Repository / TEXT("scripts/unreal"))
                && (Extension == TEXT("ts") || Extension == TEXT("py") || Extension == TEXT("cs")));
    }
    bool HasLabel(const TSharedRef<SWidget>& Widget, const FString& Label)
    {
        if (!Widget->GetVisibility().IsVisible()) return false;
        if (Widget->GetTypeAsString() == TEXT("STextBlock")
            && StaticCastSharedRef<STextBlock>(Widget)->GetText().ToString() == Label) return true;
        auto* Children = Widget->GetChildren();
        for (int32 Index = 0; Children && Index < Children->Num(); ++Index)
            if (HasLabel(Children->GetChildAt(Index), Label)) return true;
        return false;
    }
    bool Click(const TSharedRef<SWidget>& Widget, const FString& Label)
    {
        // Ancestor visibility and enabled state are honored before calling the real delegate.
        if (!Widget->GetVisibility().IsVisible() || !Widget->IsEnabled()) return false;
        if (Widget->GetTypeAsString() == TEXT("SButton"))
        {
            const auto Button = StaticCastSharedRef<SButton>(Widget);
            if (HasLabel(Button->GetContent(), Label)) { Button->SimulateClick(); return true; }
        }
        auto* Children = Widget->GetChildren();
        for (int32 Index = 0; Children && Index < Children->Num(); ++Index)
            if (Click(Children->GetChildAt(Index), Label)) return true;
        return false;
    }
    template<class T> T* VisibleWidget(AWarPlayerController* PC)
    {
        for (TObjectIterator<T> It; It; ++It)
            if (It->GetOwningPlayer() == PC && It->IsInViewport()) return *It;
        return nullptr;
    }
    TArray<TSharedPtr<FJsonValue>> Values(const FVector& Value)
    { return { MakeShared<FJsonValueNumber>(Value.X), MakeShared<FJsonValueNumber>(Value.Y), MakeShared<FJsonValueNumber>(Value.Z) }; }
    bool Array(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, int32 Count, TArray<double>& Out)
    {
        const TArray<TSharedPtr<FJsonValue>>* Entries = nullptr;
        if (!Object || !Object->TryGetArrayField(Name, Entries) || Entries->Num() != Count) return false;
        for (const auto& Entry : *Entries)
        { double Value; if (!Entry->TryGetNumber(Value) || !FMath::IsFinite(Value)) return false; Out.Add(Value); }
        return true;
    }
    bool ManifestTransform(const TSharedPtr<FJsonObject>& Object, FTransform& Out)
    {
        TArray<double> Location, Rotation, Scale;
        if (!Array(Object, TEXT("location"), 3, Location) || !Array(Object, TEXT("rotation"), 4, Rotation)
            || !Array(Object, TEXT("scale"), 3, Scale)) return false;
        const FQuat Q(Rotation[0], Rotation[1], Rotation[2], Rotation[3]);
        if (!Q.IsNormalized() || Scale[0] < .05 || Scale[1] < .05 || Scale[2] < .05
            || Scale[0] > 20 || Scale[1] > 20 || Scale[2] > 20) return false;
        Out = FTransform(Q, FVector(Location[0], Location[1], Location[2]), FVector(Scale[0], Scale[1], Scale[2]));
        return !Out.ContainsNaN();
    }
    bool PriorReport(const TSharedPtr<FJsonObject>& Report, const FString& Run, const FString& Map, const FString& Phase)
    { return Number(Report, TEXT("schemaVersion"), 1) && Boolean(Report, TEXT("passed"), true)
        && Equal(Report, TEXT("runId"), Run) && Equal(Report, TEXT("map"), Map) && Equal(Report, TEXT("phase"), Phase); }

    bool NormalScene(UWorld* World, AWarPlayerController* PC, AWarCharacter* Pawn,
        const TSharedPtr<FJsonObject>& Config, const FString& Output, const FString& Phase, FString& Error)
    {
        const FString Map = String(Config, TEXT("map"));
        if (!WarWorldEditMap::IsCitadelCampaign(Map)) return true;
        int32 Zones = 0, Portals = 0, Decor = 0, Practicals = 0, Residents = 0;
        UWarCityDefinition* City = nullptr;
        for (TActorIterator<AWarZoneAnchor> It(World); It; ++It)
        { ++Zones; if (It->ZoneId == TEXT("aegis_capital")) City = It->CityDefinition; }
        for (TActorIterator<AWarZonePortal> It(World); It; ++It) ++Portals;
        for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
            if (It->Tags.ContainsByPredicate([](FName Tag) { return Tag.ToString().StartsWith(TEXT("WarWorldObject_aegis_decor_")); })) ++Decor;
        for (TActorIterator<APointLight> It(World); It; ++It)
            if (It->ActorHasTag(TEXT("WarCitadelDecorPractical"))) ++Practicals;
        for (TActorIterator<AWarCityNpc> It(World); It; ++It)
            if (It->ActorHasTag(TEXT("WarCitadelReviewResident"))) ++Residents;
        const auto Receipt = ReadJson(String(Config, TEXT("receiptPath")));
        if (!City || City->GetPathName().LeftChop(FString(TEXT(".City")).Len()) != String(Receipt, TEXT("city"))
            || City->Revision != String(Config, TEXT("cityRevision")) || Zones != 32 || Portals != 70
            || Decor != 56 || Practicals != 34 || Residents != 8)
            return Fail(Error, FString::Printf(TEXT("Normal scene differs: zones=%d portals=%d decor=%d lights=%d residents=%d"),
                Zones, Portals, Decor, Practicals, Residents));
        TMap<FName, float> Sensitivities;
        for (const auto& Axis : GetDefault<UInputSettings>()->AxisConfig)
            if (Axis.AxisKeyName == TEXT("MouseX") || Axis.AxisKeyName == TEXT("MouseY") || Axis.AxisKeyName == TEXT("Mouse2D"))
                Sensitivities.Add(Axis.AxisKeyName, Axis.AxisProperties.Sensitivity);
        for (FName Key : { FName(TEXT("MouseX")), FName(TEXT("MouseY")), FName(TEXT("Mouse2D")) })
            if (!Sensitivities.Contains(Key) || !FMath::IsNearlyEqual(Sensitivities[Key], 1.f))
                return Fail(Error, TEXT("Normal mouse pixel axes are still attenuated by legacy sensitivity."));
        // Exercise the actual local camera handler and restore its state in the same tick.
        const FWarCameraState Before = PC->GetLocalCameraState();
        const FRotator Rotation = PC->GetControlRotation();
        FWarCameraState Expected = Before; Expected.OrbitPixels(100, 25);
        Pawn->ApplyCameraOrbit(100, 25);
        const FWarCameraState Actual = PC->GetLocalCameraState();
        PC->GetLocalCameraState() = Before; Pawn->ApplyCameraOrbit(0, 0); PC->SetControlRotation(Rotation);
        if (!FMath::IsNearlyEqual(Actual.Yaw, Expected.Yaw, .0001) || !FMath::IsNearlyEqual(Actual.Pitch, Expected.Pitch, .0001)
            || FMath::IsNearlyEqual(Actual.Yaw, Before.Yaw, .0001))
            return Fail(Error, TEXT("The actual normal-world camera did not apply its pixel orbit rules."));
        auto Scene = MakeShared<FJsonObject>();
        Scene->SetNumberField(TEXT("schemaVersion"), 1); Scene->SetBoolField(TEXT("passed"), true);
        Scene->SetStringField(TEXT("map"), Map); Scene->SetStringField(TEXT("phase"), Phase);
        Scene->SetStringField(TEXT("city"), String(Receipt, TEXT("city"))); Scene->SetStringField(TEXT("cityRevision"), City->Revision);
        Scene->SetNumberField(TEXT("zones"), Zones); Scene->SetNumberField(TEXT("directedPortals"), Portals);
        Scene->SetNumberField(TEXT("decorObjects"), Decor); Scene->SetNumberField(TEXT("practicalLights"), Practicals);
        Scene->SetNumberField(TEXT("residents"), Residents); Scene->SetBoolField(TEXT("mouseAxesUnattenuated"), true);
        Scene->SetBoolField(TEXT("actualCameraPixelHandlerVerified"), true); Scene->SetBoolField(TEXT("cameraStateRestored"), true);
        Scene->SetBoolField(TEXT("physicalMouseHardwareVerified"), false);
        Scene->SetNumberField(TEXT("cameraYawBefore"), Before.Yaw); Scene->SetNumberField(TEXT("cameraYawAfter"), Actual.Yaw);
        Scene->SetNumberField(TEXT("cameraYawExpected"), Expected.Yaw); Scene->SetNumberField(TEXT("cameraPitchAfter"), Actual.Pitch);
        Scene->SetNumberField(TEXT("cameraPitchExpected"), Expected.Pitch);
        Scene->SetBoolField(TEXT("fullSiegeAdmissionApproved"), false); Scene->SetBoolField(TEXT("releaseAcceptance"), false);
        return WriteNewJson(Output / (Phase + TEXT("-scene.json")), Scene, Error);
    }
}

namespace OrdinaryBuilder = WarOrdinaryBuilderProofPrivate;

bool UWarInterfaceProof::LoadOrdinaryBuilderConfig(FString& Error)
{
#if !UE_BUILD_DEVELOPMENT
    return OrdinaryBuilder::Fail(Error, TEXT("Ordinary draft proof requires a Development build."));
#else
    if (!FParse::Value(FCommandLine::Get(), TEXT("WarBuilderOrdinaryConfig="), OrdinaryBuilderConfigPath)
        || !OrdinaryBuilder::AbsolutePath(OrdinaryBuilderConfigPath)) return OrdinaryBuilder::Fail(Error, TEXT("An absolute ordinary proof config is required."));
    OrdinaryBuilderConfigPath = OrdinaryBuilder::Absolute(OrdinaryBuilderConfigPath);
    OrdinaryBuilderConfig = OrdinaryBuilder::ReadJson(OrdinaryBuilderConfigPath);
    if (!OrdinaryBuilderConfig) return OrdinaryBuilder::Fail(Error, TEXT("Ordinary proof config is unreadable."));
    OrdinaryBuilderRun = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("runId")); OrdinaryBuilderPhase = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("phase"));
    if (!OrdinaryBuilder::Hex(OrdinaryBuilderRun, 32) || (OrdinaryBuilderPhase != TEXT("save") && OrdinaryBuilderPhase != TEXT("publish") && OrdinaryBuilderPhase != TEXT("restore")))
        return OrdinaryBuilder::Fail(Error, TEXT("An exact proof GUID and phase are required."));
    OrdinaryBuilderOutput = OrdinaryBuilder::Absolute(FPaths::ProjectSavedDir() / TEXT("WorldEditOrdinaryProof") / OrdinaryBuilderRun);
    if (!OrdinaryBuilder::PathEqual(OrdinaryBuilderConfig, TEXT("outputDir"), OrdinaryBuilderOutput)
        || !FPaths::IsUnderDirectory(OrdinaryBuilderConfigPath, OrdinaryBuilderOutput))
        return OrdinaryBuilder::Fail(Error, TEXT("Ordinary evidence/config paths must belong to the exact private run."));
    if (!OrdinaryBuilder::Keys(OrdinaryBuilderConfig, { TEXT("schemaVersion"), TEXT("runId"), TEXT("phase"), TEXT("map"), TEXT("signature"),
        TEXT("mapSha256"), TEXT("sourceRevision"), TEXT("cityRevision"), TEXT("receiptPath"), TEXT("receiptSha256"), TEXT("binaryPath"),
        TEXT("binarySha256"), TEXT("sourceHashes"), TEXT("packageHashes"), TEXT("outputDir"), TEXT("draftPath"), TEXT("publicationPath"),
        TEXT("manifestPath"), TEXT("manifestSha256"), TEXT("preexistingWorldEditHashes") }) || !OrdinaryBuilder::Number(OrdinaryBuilderConfig, TEXT("schemaVersion"), 1))
        return OrdinaryBuilder::Fail(Error, TEXT("Ordinary proof config schema is incomplete or contains unknown fields."));
    for (const TCHAR* Name : { TEXT("signature"), TEXT("mapSha256"), TEXT("cityRevision"), TEXT("receiptSha256"), TEXT("binarySha256") })
        if (!OrdinaryBuilder::Hex(OrdinaryBuilder::String(OrdinaryBuilderConfig, Name), 64)) return OrdinaryBuilder::Fail(Error, TEXT("Ordinary proof identity needs exact SHA-256 values."));
    if (!OrdinaryBuilder::Hex(OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("sourceRevision")), 12)
        || !OrdinaryBuilder::PathEqual(OrdinaryBuilderConfig, TEXT("manifestPath"), OrdinaryBuilderOutput / TEXT("manifest.json")))
        return OrdinaryBuilder::Fail(Error, TEXT("Ordinary proof revision or manifest path is invalid."));
    if (!WarCitadelProofHash::File(OrdinaryBuilderConfigPath, OrdinaryBuilderConfigHash, Error)) return false;
    const FString Map = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("map"));
    if (OrdinaryBuilderPhase == TEXT("save"))
    {
        if (!OrdinaryBuilder::Equal(OrdinaryBuilderConfig, TEXT("publicationPath"), TEXT("")) || !OrdinaryBuilder::Equal(OrdinaryBuilderConfig, TEXT("manifestSha256"), TEXT(""))
            || IFileManager::Get().FileExists(*(OrdinaryBuilderOutput / TEXT("manifest.json"))))
            return OrdinaryBuilder::Fail(Error, TEXT("Save requires a new manifest and no publication expectation."));
    }
    else
    {
        OrdinaryBuilderManifestHash = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("manifestSha256"));
        if (!OrdinaryBuilder::Hash(OrdinaryBuilderOutput / TEXT("manifest.json"), OrdinaryBuilderManifestHash, Error)) return false;
        OrdinaryBuilderManifest = OrdinaryBuilder::ReadJson(OrdinaryBuilderOutput / TEXT("manifest.json"));
        FTransform Expected; FGuid Id;
        const FString Created = OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("id"));
        if (!OrdinaryBuilder::Keys(OrdinaryBuilderManifest, { TEXT("schemaVersion"), TEXT("runId"), TEXT("map"), TEXT("id"), TEXT("templateId"),
            TEXT("sourceIdentity"), TEXT("meshPath"), TEXT("hidden"), TEXT("location"), TEXT("rotation"), TEXT("scale") })
            || !OrdinaryBuilder::Number(OrdinaryBuilderManifest, TEXT("schemaVersion"), 1) || !OrdinaryBuilder::Equal(OrdinaryBuilderManifest, TEXT("runId"), OrdinaryBuilderRun)
            || !OrdinaryBuilder::Equal(OrdinaryBuilderManifest, TEXT("map"), Map) || !Created.StartsWith(TEXT("gm_"))
            || !FGuid::ParseExact(Created.RightChop(3), EGuidFormats::Digits, Id)
            || OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("templateId")).IsEmpty() || OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("templateId")).Len() > 128
            || !OrdinaryBuilder::Hex(OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("sourceIdentity")).Right(64), 64)
            || !OrdinaryBuilder::Equal(OrdinaryBuilderManifest, TEXT("sourceIdentity"), OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("meshPath")) + TEXT(":") + OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("sourceIdentity")).Right(64))
            || !OrdinaryBuilder::Boolean(OrdinaryBuilderManifest, TEXT("hidden"), false)
            || !OrdinaryBuilder::ManifestTransform(OrdinaryBuilderManifest, Expected)) return OrdinaryBuilder::Fail(Error, TEXT("Native sentinel manifest is invalid."));
        const auto Save = OrdinaryBuilder::ReadJson(OrdinaryBuilderOutput / TEXT("save-report.json"));
        if (!OrdinaryBuilder::PriorReport(Save, OrdinaryBuilderRun, Map, TEXT("save")) || !OrdinaryBuilder::Equal(Save, TEXT("manifestSha256"), OrdinaryBuilderManifestHash)
            || !OrdinaryBuilder::PathEqual(Save, TEXT("draftPath"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("draftPath")))
            || !OrdinaryBuilder::PathEqual(Save, TEXT("publicationPath"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("publicationPath")))
            || !OrdinaryBuilder::Equal(Save, TEXT("receiptSha256"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("receiptSha256")))
            || !OrdinaryBuilder::Equal(Save, TEXT("binarySha256"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("binarySha256"))))
            return OrdinaryBuilder::Fail(Error, TEXT("Independent load lacks the exact successful native Save receipt."));
        OrdinaryBuilderDraftHash = OrdinaryBuilder::String(Save, TEXT("draftSha256"));
        double PreviousPid = 0;
        if (!Save->TryGetNumberField(TEXT("nativePid"), PreviousPid) || PreviousPid == FPlatformProcess::GetCurrentProcessId())
            return OrdinaryBuilder::Fail(Error, TEXT("The draft must be loaded in an independent native process."));
        if (OrdinaryBuilderPhase == TEXT("restore"))
        {
            const auto Published = OrdinaryBuilder::ReadJson(OrdinaryBuilderOutput / TEXT("publish-report.json"));
            if (!OrdinaryBuilder::PriorReport(Published, OrdinaryBuilderRun, Map, TEXT("publish"))
                || !OrdinaryBuilder::Equal(Published, TEXT("manifestSha256"), OrdinaryBuilderManifestHash)
                || !OrdinaryBuilder::Equal(Published, TEXT("draftSha256"), OrdinaryBuilderDraftHash)
                || !OrdinaryBuilder::PathEqual(Published, TEXT("draftPath"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("draftPath")))
                || !OrdinaryBuilder::PathEqual(Published, TEXT("publicationPath"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("publicationPath")))
                || !OrdinaryBuilder::Equal(Published, TEXT("receiptSha256"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("receiptSha256")))
                || !OrdinaryBuilder::Equal(Published, TEXT("binarySha256"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("binarySha256")))
                || !Published->TryGetNumberField(TEXT("nativePid"), PreviousPid) || PreviousPid == FPlatformProcess::GetCurrentProcessId())
                return OrdinaryBuilder::Fail(Error, TEXT("Startup restore lacks an independent native Publish receipt."));
            OrdinaryBuilderPublicationHash = OrdinaryBuilder::String(Published, TEXT("publicationSha256"));
        }
    }
    if (IFileManager::Get().FileExists(*(OrdinaryBuilderOutput / (OrdinaryBuilderPhase + TEXT("-report.json")))))
        return OrdinaryBuilder::Fail(Error, TEXT("Preserve an existing phase receipt."));
    bOrdinaryBuilderConfigReady = true;
    return CheckOrdinaryBuilderBindings(Error);
#endif
}

bool UWarInterfaceProof::CheckOrdinaryBuilderBindings(FString& Error) const
{
    if (!bOrdinaryBuilderConfigReady || !OrdinaryBuilder::Hash(OrdinaryBuilderConfigPath, OrdinaryBuilderConfigHash, Error)) return false;
    const TCHAR* Command = FCommandLine::Get();
    for (const TCHAR* Flag : { TEXT("WarPortalProof"), TEXT("WarCapitalProof"), TEXT("WarBuilderProof"), TEXT("WarGmRenderingProof"),
        TEXT("WarExpansionProof"), TEXT("WarDutchBastionProof"), TEXT("WarTargetingProof"), TEXT("WarCombatUiProof"),
        TEXT("WarWorkshopProof"), TEXT("WarActionBarProof"), TEXT("WarBuilderReload"), TEXT("WarFrontendProof"),
        TEXT("WarScenarioMenuProof"), TEXT("WarCitadelSiegeProof") })
        if (FParse::Param(Command, Flag)) return OrdinaryBuilder::Fail(Error, FString(TEXT("Ordinary draft proof rejects conflicting proof modes: ")) + Flag);
    if (!FParse::Param(Command, TEXT("WarDevelopmentGM")) || !FParse::Param(Command, TEXT("WarInterfaceProof")))
        return OrdinaryBuilder::Fail(Error, TEXT("Explicit Development GM and interface proof admission are required."));
    const UWorld* World = GetWorld();
    const FString Map = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("map")); FString Selected;
    GConfig->GetString(TEXT("/Script/EngineSettings.GameMapsSettings"), TEXT("GameDefaultMap"), Selected, GEngineIni);
    if (!World || World->GetNetMode() != NM_Standalone || World->WorldType != EWorldType::Game
        || UWorld::RemovePIEPrefix(World->GetOutermost()->GetName()) != Map || Selected != Map
        || (!WarWorldEditMap::IsCitadelHumanReview(Map) && !WarWorldEditMap::IsCitadelCampaign(Map))
        || !WarWorldEditMap::IsSupported(Map, Selected))
        return OrdinaryBuilder::Fail(Error, TEXT("The exact selected citadel must be a standalone Development game world."));
    const bool bReview = WarWorldEditMap::IsCitadelHumanReview(Map);
    if (!bReview && FString(Command).Contains(TEXT("GameDefaultMap="), ESearchCase::IgnoreCase))
        return OrdinaryBuilder::Fail(Error, TEXT("Normal campaign proof cannot override the configured default map."));
    const auto* PC = Cast<AWarPlayerController>(World->GetFirstPlayerController());
    if (PC && (!PC->HasAuthority() || !PC->IsLocalController() || !PC->GetEntryFailure().IsEmpty()))
        return OrdinaryBuilder::Fail(Error, TEXT("Local GM authority or character entry was rejected."));
    const auto* Editor = World->GetSubsystem<UWarWorldEditSubsystem>();
    const FString Draft = OrdinaryBuilder::Absolute(FPaths::ProjectSavedDir() / WarWorldEditMap::OrdinaryDraftRelativePath(Map));
    if (!Editor || !OrdinaryBuilder::PathEqual(OrdinaryBuilderConfig, TEXT("draftPath"), Draft) || !FPaths::IsSamePath(OrdinaryBuilder::Absolute(Editor->GetDraftLocation()), Draft))
        return OrdinaryBuilder::Fail(Error, TEXT("Native draft storage is not the selected map's ordinary path."));
    const FString Publication = OrdinaryBuilder::Absolute(Editor->GetPublicationLocation());
    if (!FPaths::IsSamePath(FPaths::GetPath(Publication), FPaths::GetPath(Draft))
        || (OrdinaryBuilderPhase != TEXT("save") && !OrdinaryBuilder::PathEqual(OrdinaryBuilderConfig, TEXT("publicationPath"), Publication)))
        return OrdinaryBuilder::Fail(Error, TEXT("Native publication is not the exact ordinary map publication."));
    const FString Binary = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("binaryPath"));
    if (!OrdinaryBuilder::AbsolutePath(Binary) || !FPaths::IsUnderDirectory(Binary, OrdinaryBuilder::Absolute(FPaths::ProjectDir() / TEXT("Binaries")))
        || !FPaths::IsSamePath(Binary, OrdinaryBuilder::Absolute(FModuleManager::Get().GetModuleFilename(TEXT("AegisWar"))))
        || !OrdinaryBuilder::Hash(Binary, OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("binarySha256")), Error))
        return OrdinaryBuilder::Fail(Error, TEXT("The loaded AegisWar module does not match the explicit byte binding."));
    const FString ReceiptPath = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("receiptPath"));
    if (!OrdinaryBuilder::AbsolutePath(ReceiptPath) || !OrdinaryBuilder::Hash(ReceiptPath, OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("receiptSha256")), Error)) return false;
    const auto Receipt = OrdinaryBuilder::ReadJson(ReceiptPath);
    if (!OrdinaryBuilder::Number(Receipt, TEXT("schemaVersion"), 1) || !OrdinaryBuilder::Equal(Receipt, TEXT("map"), Map)
        || !OrdinaryBuilder::Equal(Receipt, TEXT("signature"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("signature")))
        || !OrdinaryBuilder::Equal(Receipt, TEXT("mapSha256"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("mapSha256")))
        || !OrdinaryBuilder::Equal(Receipt, TEXT("sourceRevision"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("sourceRevision")))
        || !OrdinaryBuilder::Equal(Receipt, TEXT("cityRevision"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("cityRevision")))
        || !OrdinaryBuilder::Boolean(Receipt, TEXT("sourcePackagesUnchanged"), true) || !OrdinaryBuilder::Boolean(Receipt, TEXT("requiresDevelopmentGM"), true)
        || !OrdinaryBuilder::Boolean(Receipt, TEXT("ordinaryLocalDevelopmentEntry"), true) || !OrdinaryBuilder::Boolean(Receipt, TEXT("servicesRetained"), true)
        || !OrdinaryBuilder::Boolean(Receipt, TEXT("residentPopulationPrivateReviewOnly"), bReview) || !OrdinaryBuilder::Boolean(Receipt, TEXT("published"), false)
        || !OrdinaryBuilder::Boolean(Receipt, TEXT("visualApproved"), false) || !OrdinaryBuilder::Boolean(Receipt, TEXT("gameplayApproved"), false))
        return OrdinaryBuilder::Fail(Error, TEXT("The fresh private wrapper receipt changed or lost its exact identity."));
    if (!bReview && (!OrdinaryBuilder::Boolean(Receipt, TEXT("developmentOnly"), true)
        || !OrdinaryBuilder::Boolean(Receipt, TEXT("defaultMapSelected"), true)
        || !OrdinaryBuilder::Boolean(Receipt, TEXT("fullSiegeAdmissionApproved"), false)))
        return OrdinaryBuilder::Fail(Error, TEXT("Normal campaign receipt cannot grant competitive or release acceptance."));
    const FString Prefix = FPaths::GetPath(Map);
    if (!Prefix.EndsWith(TEXT("_") + OrdinaryBuilder::String(Receipt, TEXT("signature")).Left(12)))
        return OrdinaryBuilder::Fail(Error, TEXT("The wrapper signature does not qualify its native map identity."));
    const TSharedPtr<FJsonObject>* Packages = nullptr; auto Union = MakeShared<FJsonObject>();
    for (const TCHAR* Name : { TEXT("sourcePackageHashes"), TEXT("packageHashes") })
    {
        const TSharedPtr<FJsonObject>* Entries = nullptr;
        if (!Receipt->TryGetObjectField(Name, Entries) || (*Entries)->Values.IsEmpty()) return OrdinaryBuilder::Fail(Error, TEXT("The wrapper package ledger is missing."));
        for (const auto& Pair : (*Entries)->Values)
        {
            FString Value;
            if (!Pair.Value->TryGetString(Value) || !OrdinaryBuilder::Hex(Value, 64) || (Union->HasField(Pair.Key) && !OrdinaryBuilder::Equal(Union, *Pair.Key, Value)))
                return OrdinaryBuilder::Fail(Error, TEXT("The wrapper has conflicting package bytes."));
            Union->SetStringField(Pair.Key, Value);
        }
    }
    if (!OrdinaryBuilderConfig->TryGetObjectField(TEXT("packageHashes"), Packages) || (*Packages)->Values.Num() > 4096
        || !OrdinaryBuilder::SameTable(Union, *Packages) || !OrdinaryBuilder::Equal(*Packages, *Map, OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("mapSha256"))))
        return OrdinaryBuilder::Fail(Error, TEXT("The config package set differs from the exact wrapper receipt."));
    for (const auto& Pair : (*Packages)->Values)
    {
        const FString Key(Pair.Key.Len(), *Pair.Key);
        FString Filename, Expected;
        if (!(Key.StartsWith(TEXT("/Game/")) || Key.StartsWith(TEXT("/Engine/")))
            || !FPackageName::IsValidLongPackageName(Key, true) || !FPackageName::DoesPackageExist(Key, &Filename)
            || !Pair.Value->TryGetString(Expected) || !OrdinaryBuilder::Hash(Filename, Expected, Error)) return OrdinaryBuilder::Fail(Error, TEXT("A preserved native wrapper package changed."));
    }
    const TSharedPtr<FJsonObject>* Sources = nullptr;
    if (!OrdinaryBuilderConfig->TryGetObjectField(TEXT("sourceHashes"), Sources) || (*Sources)->Values.IsEmpty() || (*Sources)->Values.Num() > 8192)
        return OrdinaryBuilder::Fail(Error, TEXT("The complete native/config/tool source binding is required."));
    TSet<FString> Bound;
    for (const auto& Pair : (*Sources)->Values)
    {
        const FString Key(Pair.Key.Len(), *Pair.Key);
        FString Expected;
        if (!OrdinaryBuilder::AbsolutePath(Key) || !OrdinaryBuilder::BoundSource(Key) || Bound.Contains(OrdinaryBuilder::Identity(Key))
            || !Pair.Value->TryGetString(Expected) || !OrdinaryBuilder::Hash(Key, Expected, Error)) return OrdinaryBuilder::Fail(Error, TEXT("A native/config/tool source changed or escaped its binding."));
        Bound.Add(OrdinaryBuilder::Identity(Key));
    }
    TSet<FString> Actual;
    const FString Project = OrdinaryBuilder::Absolute(FPaths::ProjectDir()), Repository = OrdinaryBuilder::Absolute(Project / TEXT("../.."));
    for (const FString& Root : { Project / TEXT("Source"), Project / TEXT("Config"), Repository / TEXT("scripts/unreal") })
    {
        TArray<FString> Files; IFileManager::Get().FindFilesRecursive(Files, *Root, TEXT("*"), true, false);
        for (const FString& File : Files) if (OrdinaryBuilder::BoundSource(OrdinaryBuilder::Absolute(File))) Actual.Add(OrdinaryBuilder::Identity(File));
    }
    if (Actual.Num() != Bound.Num()) return OrdinaryBuilder::Fail(Error, TEXT("The source binding omits or adds project files."));
    for (const FString& File : Actual) if (!Bound.Contains(File)) return OrdinaryBuilder::Fail(Error, TEXT("The complete source set changed."));
    for (const FString& Required : { Project / TEXT("Source/AegisWar/AegisWar.Build.cs"),
        Project / TEXT("Source/AegisWar/Private/WarWorldBuilderOrdinaryProof.cpp"),
        Project / TEXT("Source/AegisWar/Public/WarInterfaceProof.h"),
        Project / TEXT("Source/AegisWarEditorTools/AegisWarEditorTools.Build.cs"), Project / TEXT("Config/DefaultEngine.ini") })
        if (!Bound.Contains(OrdinaryBuilder::Identity(Required))) return OrdinaryBuilder::Fail(Error, TEXT("The runtime, Editor module, proof and project config must be bound."));
    const TSharedPtr<FJsonObject>* Existing = nullptr; TSet<FString> Known;
    const FString Storage = OrdinaryBuilder::Absolute(FPaths::ProjectSavedDir() / TEXT("WorldEdit"));
    if (!OrdinaryBuilderConfig->TryGetObjectField(TEXT("preexistingWorldEditHashes"), Existing) || (*Existing)->Values.Num() > 16384)
        return OrdinaryBuilder::Fail(Error, TEXT("The original WorldEdit byte ledger is required."));
    for (const auto& Pair : (*Existing)->Values)
    {
        const FString Key(Pair.Key.Len(), *Pair.Key);
        FString Expected;
        if (!OrdinaryBuilder::AbsolutePath(Key) || !FPaths::IsUnderDirectory(Key, Storage) || FPaths::IsUnderDirectory(Key, FPaths::GetPath(Draft))
            || Known.Contains(OrdinaryBuilder::Identity(Key)) || !Pair.Value->TryGetString(Expected) || !OrdinaryBuilder::Hash(Key, Expected, Error))
            return OrdinaryBuilder::Fail(Error, TEXT("Preserve original WorldEdit files; the byte ledger changed."));
        Known.Add(OrdinaryBuilder::Identity(Key));
    }
    if (!OrdinaryBuilderDraftHash.IsEmpty())
    { if (!OrdinaryBuilder::Hash(Draft, OrdinaryBuilderDraftHash, Error)) return false; Known.Add(OrdinaryBuilder::Identity(Draft)); }
    if (!OrdinaryBuilderPublicationHash.IsEmpty())
    { if (!OrdinaryBuilder::Hash(Publication, OrdinaryBuilderPublicationHash, Error)) return false; Known.Add(OrdinaryBuilder::Identity(Publication)); }
    TArray<FString> All; IFileManager::Get().FindFilesRecursive(All, *Storage, TEXT("*"), true, false);
    for (const FString& File : All) if (!Known.Contains(OrdinaryBuilder::Identity(File)))
        return OrdinaryBuilder::Fail(Error, TEXT("Preserve unexpected WorldEdit files, locks or temporary bytes: ") + File);
    TArray<FString> TargetEntries;
    IFileManager::Get().FindFiles(TargetEntries, *(FPaths::GetPath(Draft) / TEXT("*")), true, true);
    for (const FString& Entry : TargetEntries)
        if (!Known.Contains(OrdinaryBuilder::Identity(FPaths::GetPath(Draft) / Entry))) return OrdinaryBuilder::Fail(Error, TEXT("Preserve unexpected entries in the ordinary wrapper directory."));
    // FindFilesRecursive above rejects every foreign target file, including save/publication locks.
    if (OrdinaryBuilderDraftHash.IsEmpty() && IFileManager::Get().FileExists(*Draft)) return OrdinaryBuilder::Fail(Error, TEXT("Preserve an existing ordinary draft."));
    if (OrdinaryBuilderPublicationHash.IsEmpty() && IFileManager::Get().FileExists(*Publication)) return OrdinaryBuilder::Fail(Error, TEXT("Preserve an existing ordinary publication."));
    if (!OrdinaryBuilderManifestHash.IsEmpty() && !OrdinaryBuilder::Hash(OrdinaryBuilderOutput / TEXT("manifest.json"), OrdinaryBuilderManifestHash, Error)) return false;
    return true;
}

bool UWarInterfaceProof::CheckOrdinaryBuilderSentinel(FString& Error) const
{
    if (!OrdinaryBuilderManifest) return OrdinaryBuilder::Fail(Error, TEXT("The exact native sentinel manifest is required."));
    const auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    const FName Id(*OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("id"))); FTransform Expected;
    const auto* Row = Editor ? Editor->GetHistory().Find(Id) : nullptr;
    const auto* Actor = Editor ? Cast<AStaticMeshActor>(Editor->GetObjectActor(Id)) : nullptr;
    const auto* Component = IsValid(Actor) ? Actor->GetStaticMeshComponent() : nullptr;
    const auto* Mesh = Component ? Component->GetStaticMesh().Get() : nullptr;
    if (!Row || !IsValid(Mesh) || !IsValid(Component) || !Component->IsRegistered() || !Actor->GetRootComponent() || !OrdinaryBuilder::ManifestTransform(OrdinaryBuilderManifest, Expected)
        || Row->Id.ToString() != OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("id"))
        || Row->TemplateId.ToString() != OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("templateId"))
        || Row->SourceIdentity != OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("sourceIdentity"))
        || Mesh->GetPathName() != OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("meshPath"))
        || !Mesh->GetPathName().StartsWith(TEXT("/Game/")) || !FPackageName::IsValidObjectPath(Mesh->GetPathName())
        || !OrdinaryBuilder::Hex(Row->SourceIdentity.Right(64), 64)
        || !OrdinaryBuilder::Equal(OrdinaryBuilderManifest, TEXT("sourceIdentity"), Mesh->GetPathName() + TEXT(":") + Row->SourceIdentity.Right(64))
        || !OrdinaryBuilder::Boolean(OrdinaryBuilderManifest, TEXT("hidden"), Row->bHidden) || Actor->IsHidden() != Row->bHidden
        || !Row->Transform.Equals(Expected, .0001) || !Actor->GetActorTransform().Equals(Expected, .0001))
        return OrdinaryBuilder::Fail(Error, TEXT("The exact persisted sentinel row/model/visibility/actor transform was not restored."));
    TArray<FWarWorldEditPracticalLight> Practicals;
    AActor* TemplateActor = Editor->GetObjectActor(Row->TemplateId);
    if (!TemplateActor || !WarWorldEditPracticalLights::Capture(TemplateActor, Practicals, Error)
        || !WarWorldEditPracticalLights::MatchesCreated(Actor, Practicals))
        return OrdinaryBuilder::Fail(Error, TEXT("Persisted furnishing practical lights differ from the trusted authored assembly."));
    return true;
}

void UWarInterfaceProof::FinishOrdinaryBuilder(bool Passed, const FString& Detail)
{
    bFinished = true; FString Error, Result = Detail;
    if (bOrdinaryBuilderConfigReady && !CheckOrdinaryBuilderBindings(Error)) { Passed = false; Result += TEXT(" Preservation/binding failure: ") + Error; }
    if (!OrdinaryBuilderOutput.IsEmpty() && OrdinaryBuilder::Hex(OrdinaryBuilderRun, 32)
        && (OrdinaryBuilderPhase == TEXT("save") || OrdinaryBuilderPhase == TEXT("publish") || OrdinaryBuilderPhase == TEXT("restore")))
    {
        auto Report = MakeShared<FJsonObject>(); Report->SetNumberField(TEXT("schemaVersion"), 1); Report->SetBoolField(TEXT("passed"), Passed);
        Report->SetStringField(TEXT("runId"), OrdinaryBuilderRun); Report->SetStringField(TEXT("phase"), OrdinaryBuilderPhase);
        Report->SetStringField(TEXT("map"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("map"))); Report->SetStringField(TEXT("configSha256"), OrdinaryBuilderConfigHash);
        Report->SetStringField(TEXT("receiptSha256"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("receiptSha256")));
        Report->SetStringField(TEXT("binarySha256"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("binarySha256")));
        const FString ConfigDraft = OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("draftPath"));
        Report->SetStringField(TEXT("draftPath"), ConfigDraft.IsEmpty() ? FString() : OrdinaryBuilder::Absolute(ConfigDraft));
        const auto* Editor = GetWorld() ? GetWorld()->GetSubsystem<UWarWorldEditSubsystem>() : nullptr;
        Report->SetStringField(TEXT("publicationPath"), Editor ? OrdinaryBuilder::Absolute(Editor->GetPublicationLocation()) : OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("publicationPath")));
        Report->SetStringField(TEXT("manifestSha256"), OrdinaryBuilderManifestHash); Report->SetStringField(TEXT("draftSha256"), OrdinaryBuilderDraftHash);
        Report->SetStringField(TEXT("publicationSha256"), OrdinaryBuilderPublicationHash);
        Report->SetBoolField(TEXT("guiOpened"), bOrdinaryBuilderGuiOpened); Report->SetBoolField(TEXT("saveClicked"), bOrdinaryBuilderSaveClicked);
        Report->SetBoolField(TEXT("loadClicked"), bOrdinaryBuilderLoadClicked); Report->SetBoolField(TEXT("publishClicked"), bOrdinaryBuilderPublishClicked);
        Report->SetBoolField(TEXT("startupRestored"), bOrdinaryBuilderStartupRestored);
        Report->SetBoolField(TEXT("fixtureAdmission"), true); Report->SetBoolField(TEXT("ordinaryLoginVerified"), false);
        Report->SetBoolField(TEXT("sharedPublication"), false); Report->SetBoolField(TEXT("visualApproved"), false); Report->SetBoolField(TEXT("gameplayApproved"), false);
        Report->SetNumberField(TEXT("nativePid"), FPlatformProcess::GetCurrentProcessId()); Report->SetStringField(TEXT("detail"), Result);
        if (!OrdinaryBuilder::WriteNewJson(OrdinaryBuilderOutput / (OrdinaryBuilderPhase + TEXT("-report.json")), Report, Error))
        { Passed = false; UE_LOG(LogTemp, Error, TEXT("Ordinary draft proof evidence failure: %s"), *Error); }
    }
    UE_LOG(LogTemp, Display, TEXT("Ordinary draft proof passed=%d: %s"), Passed, *Result);
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}

void UWarInterfaceProof::TickWorldBuilderOrdinary(double Now)
{
    if (!OrdinaryBuilderStarted) OrdinaryBuilderStarted = FPlatformTime::Seconds();
    FString Error;
    if (!bOrdinaryBuilderConfigReady && !LoadOrdinaryBuilderConfig(Error)) { FinishOrdinaryBuilder(false, Error); return; }
    if (FPlatformTime::Seconds() - OrdinaryBuilderStarted > 180) { FinishOrdinaryBuilder(false, TEXT("Ordinary GM persistence proof timed out.")); return; }
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!PC || !Pawn || !Pawn->IsVisualReady() || !Editor || Editor->GetHistory().GetBaselineObjects().IsEmpty()) return;
    const auto Check = [this](bool Good, const FString& Detail) { if (!Good) FinishOrdinaryBuilder(false, Detail); return Good; };
    if (!Check(Editor->CanUse(PC) && Editor->GetPublicationLoadError().IsEmpty(), TEXT("Ordinary startup GM publication initialization failed."))) return;
    if (Step == 0)
    {
        if (!Check(CheckOrdinaryBuilderBindings(Error), Error)) return;
        if (!Check(OrdinaryBuilder::NormalScene(GetWorld(), PC, Pawn, OrdinaryBuilderConfig,
            OrdinaryBuilderOutput, OrdinaryBuilderPhase, Error), Error)) return;
        // PlayerTick owns initialization. The proof must never manufacture startup restoration by calling Open.
        if (OrdinaryBuilderPhase == TEXT("restore"))
        {
            if (!Check(!PC->IsWorldEditorOpen() && !PC->IsInterfaceOpen(), TEXT("Startup restoration must precede opening GM controls."))) return;
            if (!Check(CheckOrdinaryBuilderSentinel(Error), Error)) return;
            bOrdinaryBuilderStartupRestored = true; FinishOrdinaryBuilder(true, TEXT("Exact local publication restored before opening GM controls.")); return;
        }
        if (OrdinaryBuilderPhase == TEXT("publish"))
        {
            const FName Id(*OrdinaryBuilder::String(OrdinaryBuilderManifest, TEXT("id")));
            if (!Check(!Editor->GetHistory().Find(Id) && !Editor->GetObjectActor(Id), TEXT("A saved draft was applied before the GUI Load action."))) return;
        }
        else for (const auto& Row : Editor->GetHistory().GetObjects()) OrdinaryBuilderInitialIds.Add(Row.Id);
        PC->ToggleMenu();
    }
    else if (Step == 1)
    {
        auto* Menu = OrdinaryBuilder::VisibleWidget<UWarInterfaceWidget>(PC);
        if (!Check(Menu && OrdinaryBuilder::Click(Menu->TakeWidget(), TEXT("GM Tools")) && Menu->GetPage() == TEXT("GM Tools"), TEXT("Enabled GM Tools navigation was unavailable."))) return;
    }
    else if (Step == 2)
    {
        if (!Check(CheckOrdinaryBuilderBindings(Error), Error)) return;
        auto* Menu = OrdinaryBuilder::VisibleWidget<UWarInterfaceWidget>(PC);
        if (!Check(Menu && OrdinaryBuilder::Click(Menu->TakeWidget(), TEXT("Open world builder")) && PC->IsWorldEditorOpen()
            && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(), TEXT("The actual GM Open world builder action failed."))) return;
        bOrdinaryBuilderGuiOpened = true;
    }
    else
    {
        auto* Widget = OrdinaryBuilder::VisibleWidget<UWarWorldEditWidget>(PC);
        if (!Check(Widget != nullptr, TEXT("The actual world builder widget is missing."))) return;
        if (OrdinaryBuilderPhase == TEXT("publish"))
        {
            if (Step == 3)
            {
                if (!Check(CheckOrdinaryBuilderBindings(Error), Error)) return;
                const bool Clicked = OrdinaryBuilder::Click(Widget->TakeWidget(), TEXT("Load draft"));
                const bool Loaded = PC->GetWorldEditMessage().StartsWith(TEXT("Saved draft loaded."))
                    || PC->GetWorldEditMessage().StartsWith(TEXT("Draft loaded;"));
                if (!Check(Clicked && Loaded && CheckOrdinaryBuilderSentinel(Error),
                    TEXT("The actual Load draft action failed: ") + Error + TEXT(" ") + PC->GetWorldEditMessage())) return;
                bOrdinaryBuilderLoadClicked = true;
            }
            else if (Step == 4)
            {
                if (!Check(CheckOrdinaryBuilderBindings(Error) && CheckOrdinaryBuilderSentinel(Error), Error)) return;
                if (!Check(OrdinaryBuilder::Click(Widget->TakeWidget(), TEXT("Publish draft to local game"))
                    && PC->GetWorldEditMessage().StartsWith(TEXT("Published to this local game.")), TEXT("The actual local Publish action failed: ") + PC->GetWorldEditMessage())) return;
                bOrdinaryBuilderPublishClicked = true;
                if (!Check(WarCitadelProofHash::File(Editor->GetPublicationLocation(), OrdinaryBuilderPublicationHash, Error), Error)) return;
            }
            else
            {
                if (!Check(CheckOrdinaryBuilderSentinel(Error), Error)) return;
                FinishOrdinaryBuilder(true, TEXT("Independent GUI Load restored the exact saved sentinel; local Publish succeeded.")); return;
            }
        }
        else if (Step == 3)
        {
            double Best = TNumericLimits<double>::Max(); FString Label; bool bLit = false;
            for (const auto& Entry : WarWorldEditCatalog::Build(Editor->GetHistory().GetBaselineObjects()))
                if (const auto* Mesh = Editor->GetTemplateMesh(Entry.TemplateId))
                {
                    TArray<FWarWorldEditPracticalLight> Practicals;
                    AActor* Authored = Editor->GetObjectActor(Entry.TemplateId);
                    const bool bCandidateLit = Authored && WarWorldEditPracticalLights::Capture(Authored, Practicals, Error) && !Practicals.IsEmpty();
                    const double Size = Mesh->GetBoundingBox().GetExtent().Size();
                    if ((bCandidateLit && !bLit) || (bCandidateLit == bLit && Size < Best))
                    { bLit = bCandidateLit; Best = Size; BuilderTemplate = Entry.TemplateId; Label = Entry.Label; }
                }
            if (!Check(!Label.IsEmpty() && OrdinaryBuilder::Click(Widget->TakeWidget(), Label) && Widget->HasPlacement()
                && IsValid(Widget->PreviewActor) && !Widget->PreviewActor->GetActorEnableCollision(), TEXT("The enabled catalog selection did not create a model preview."))) return;
            int32 Width, Height; PC->GetViewportSize(Width, Height); bool Found = false;
            for (int32 Y = Height * 3 / 4; Y < Height * 9 / 10 && !Found; Y += 15)
                for (int32 X = Width * 2 / 3; X < Width * 9 / 10 && !Found; X += 15)
                {
                    FVector Origin, Direction; FTransform Placement;
                    if (PC->DeprojectScreenPositionToWorld(X, Y, Origin, Direction)
                        && Editor->ResolvePlacement(PC, BuilderTemplate, Origin, Direction, 0, 0, Placement, Error))
                    { PC->SetMouseLocation(X, Y); Found = true; }
                }
            if (!Check(Found, TEXT("No visible authored support surface was available for GUI placement."))) return;
        }
        else if (Step == 4)
        {
            if (!Check(CheckOrdinaryBuilderBindings(Error), Error)) return;
            if (!Check(Widget->bPreviewValid && IsValid(Widget->PreviewActor) && !Widget->PreviewActor->IsHidden(), TEXT("Pointer placement preview is not valid and visible."))) return;
            PC->PickWorldEditorObject();
            const FWarWorldEditObject* Created = nullptr; int32 Added = 0;
            for (const auto& Row : Editor->GetHistory().GetObjects()) if (!OrdinaryBuilderInitialIds.Contains(Row.Id)) { ++Added; Created = &Row; }
            const auto* Actor = Created ? Cast<AStaticMeshActor>(Editor->GetObjectActor(Created->Id)) : nullptr;
            const auto* Mesh = IsValid(Actor) && Actor->GetStaticMeshComponent() ? Actor->GetStaticMeshComponent()->GetStaticMesh().Get() : nullptr;
            if (!Check(!Widget->HasPlacement() && Added == 1 && Created && Mesh && Created->TemplateId == BuilderTemplate && !Created->bHidden,
                TEXT("Pointer placement did not create exactly one trusted visible model."))) return;
            OrdinaryBuilderManifest = MakeShared<FJsonObject>(); OrdinaryBuilderManifest->SetNumberField(TEXT("schemaVersion"), 1);
            OrdinaryBuilderManifest->SetStringField(TEXT("runId"), OrdinaryBuilderRun); OrdinaryBuilderManifest->SetStringField(TEXT("map"), OrdinaryBuilder::String(OrdinaryBuilderConfig, TEXT("map")));
            OrdinaryBuilderManifest->SetStringField(TEXT("id"), Created->Id.ToString()); OrdinaryBuilderManifest->SetStringField(TEXT("templateId"), Created->TemplateId.ToString());
            OrdinaryBuilderManifest->SetStringField(TEXT("sourceIdentity"), Created->SourceIdentity); OrdinaryBuilderManifest->SetStringField(TEXT("meshPath"), Mesh->GetPathName());
            OrdinaryBuilderManifest->SetBoolField(TEXT("hidden"), Created->bHidden);
            OrdinaryBuilderManifest->SetArrayField(TEXT("location"), OrdinaryBuilder::Values(Created->Transform.GetLocation()));
            OrdinaryBuilderManifest->SetArrayField(TEXT("scale"), OrdinaryBuilder::Values(Created->Transform.GetScale3D())); const FQuat Q = Created->Transform.GetRotation();
            OrdinaryBuilderManifest->SetArrayField(TEXT("rotation"), { MakeShared<FJsonValueNumber>(Q.X), MakeShared<FJsonValueNumber>(Q.Y), MakeShared<FJsonValueNumber>(Q.Z), MakeShared<FJsonValueNumber>(Q.W) });
            if (!Check(CheckOrdinaryBuilderSentinel(Error) && OrdinaryBuilder::WriteNewJson(OrdinaryBuilderOutput / TEXT("manifest.json"), OrdinaryBuilderManifest.ToSharedRef(), Error)
                && WarCitadelProofHash::File(OrdinaryBuilderOutput / TEXT("manifest.json"), OrdinaryBuilderManifestHash, Error), Error)) return;
        }
        else if (Step == 5)
        {
            if (!Check(CheckOrdinaryBuilderBindings(Error) && CheckOrdinaryBuilderSentinel(Error), Error)) return;
            if (!Check(OrdinaryBuilder::Click(Widget->TakeWidget(), TEXT("Save draft")) && PC->GetWorldEditMessage() == TEXT("Draft saved locally."),
                TEXT("The actual Save draft action failed: ") + PC->GetWorldEditMessage())) return;
            bOrdinaryBuilderSaveClicked = true;
            if (!Check(WarCitadelProofHash::File(Editor->GetDraftLocation(), OrdinaryBuilderDraftHash, Error), Error)) return;
        }
        else
        {
            if (!Check(CheckOrdinaryBuilderSentinel(Error), Error)) return;
            FinishOrdinaryBuilder(true, TEXT("Actual GM GUI catalog placement and ordinary Save succeeded without publication.")); return;
        }
    }
    ++Step; NextStep = Now + 1;
}
