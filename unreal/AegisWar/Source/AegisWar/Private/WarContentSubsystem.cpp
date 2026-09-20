#include "WarContentSubsystem.h"
#include "AegisWar.h"
#include "WarRuntimeSettings.h"
#include "WarTypes.h"
#include "WarCharacterVisualDefinition.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    bool ArrayCount(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, int32& Out)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Object.IsValid() || !Object->TryGetArrayField(Key, Values)) return false;
        Out = Values->Num();
        return true;
    }

    bool CountNested(const TSharedPtr<FJsonObject>& Root, const TCHAR* Key, const TCHAR* ArrayKey, int32& Out)
    {
        const TSharedPtr<FJsonObject>* Object = nullptr;
        return Root->TryGetObjectField(Key, Object) && ArrayCount(*Object, ArrayKey, Out);
    }

    bool ReadMaps(const TSharedPtr<FJsonObject>& Root, const TCHAR* Key, TSet<FString>& Ids, int32& Count)
    {
        const TArray<TSharedPtr<FJsonValue>>* Maps = nullptr;
        if (!Root->TryGetArrayField(Key, Maps)) return false;
        for (const TSharedPtr<FJsonValue>& Entry : *Maps)
        {
            if (!Entry.IsValid() || Entry->Type != EJson::Object) return false;
            const TSharedPtr<FJsonObject> Map = Entry->AsObject();
            const TSharedPtr<FJsonObject>* Definition = nullptr;
            FString Id, DefinedId, SourcePath;
            if (!Map->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty() || Ids.Contains(Id)
                || !Map->TryGetStringField(TEXT("sourcePath"), SourcePath) || SourcePath.IsEmpty()
                || !Map->TryGetObjectField(TEXT("definition"), Definition)
                || !(*Definition)->TryGetStringField(TEXT("id"), DefinedId) || DefinedId != Id) return false;
            Ids.Add(Id);
        }
        Count = Maps->Num();
        return true;
    }

    bool ProjectObjectPath(const FString& Path)
    {
        const FSoftObjectPath AssetPath(Path);
        return AssetPath.IsValid() && AssetPath.GetLongPackageName().StartsWith(TEXT("/Game/"))
            && !AssetPath.GetAssetName().IsEmpty() && Path == AssetPath.ToString();
    }
}

bool UWarContentSubsystem::ParseManifest(const FString& Json, FWarContentSummary& OutSummary, FString& OutError)
{
    OutSummary = {};
    OutError.Reset();
    TSharedPtr<FJsonObject> Root;
    const auto Reject = [&OutError](const TCHAR* Message) { OutError = Message; return false; };
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
        return Reject(TEXT("Content manifest is not a JSON object."));
    double Version = 0;
    if (!Root->TryGetNumberField(TEXT("schemaVersion"), Version) || Version != 1)
        return Reject(TEXT("Content manifest requires schemaVersion 1."));
    const TSharedPtr<FJsonObject>* Source = nullptr;
    FWarContentSummary Summary;
    if (!Root->TryGetObjectField(TEXT("source"), Source)
        || !(*Source)->TryGetStringField(TEXT("sha256"), Summary.SourceSha256)
        || !WarValidation::IsSha256(Summary.SourceSha256))
        return Reject(TEXT("Content manifest source fingerprint is missing or malformed."));
    TSet<FString> Ids;
    if (!ReadMaps(Root, TEXT("maps"), Ids, Summary.MapCount) || Summary.MapCount == 0
        || !ReadMaps(Root, TEXT("developmentMaps"), Ids, Summary.DevelopmentMapCount))
        return Reject(TEXT("Content maps require unique stable IDs matching their definitions."));
    if (!CountNested(Root, TEXT("careers"), TEXT("classes"), Summary.CareerCount)
        || !CountNested(Root, TEXT("abilities"), TEXT("definitions"), Summary.AbilityCount)
        || !CountNested(Root, TEXT("items"), TEXT("definitions"), Summary.ItemCount)
        || !ArrayCount(Root, TEXT("quests"), Summary.QuestCount)
        || !CountNested(Root, TEXT("crafting"), TEXT("recipes"), Summary.RecipeCount))
        return Reject(TEXT("Content manifest is missing required gameplay catalog arrays."));
    OutSummary = Summary;
    return true;
}

void UWarContentSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    const FString Relative = GetDefault<UWarRuntimeSettings>()->ContentManifestRelativePath;
    if (!FPaths::IsRelative(Relative) || Relative.Contains(TEXT("..")))
    {
        ValidationError = TEXT("Content manifest must stay inside the project Content directory.");
        return;
    }
    FString Json;
    const FString Filename = FPaths::Combine(FPaths::ProjectContentDir(), Relative);
    if (!FFileHelper::LoadFileToString(Json, *Filename))
    {
        ValidationError = FString::Printf(TEXT("Content manifest is absent: %s. Run the migration staging command."), *Relative);
    }
    else
    {
        bReady = ParseManifest(Json, Summary, ValidationError);
        if (bReady) FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Manifest);
    }
    if (!bReady)
    {
        UE_LOG(LogAegisWar, Error, TEXT("%s"), *ValidationError);
    }
    else
    {
        UE_LOG(LogAegisWar, Display, TEXT("Catalog loaded: %d maps, %d careers, %d ability definitions. Gameplay implementation remains separate."),
            Summary.MapCount, Summary.CareerCount, Summary.AbilityCount);
    }
    FString ImportsJson;
    if (!FFileHelper::LoadFileToString(ImportsJson, *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/visual-imports.json"))))
        VisualImportError = TEXT("Verified visual-imports.json is missing. Complete an actual character import before entry.");
    else ParseVisualImports(ImportsJson, VisualImports, VisualImportError);
}

bool UWarContentSubsystem::ParseVisualImports(const FString& Json, TMap<FName, FWarVisualImportBinding>& OutBindings, FString& OutError)
{
    OutBindings.Reset();
    OutError.Reset();
    const auto Reject = [&OutError](const TCHAR* Message) { OutError = Message; return false; };
    TSharedPtr<FJsonObject> Root;
    double Version = 0;
    const TArray<TSharedPtr<FJsonValue>>* Entries = nullptr;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid()
        || !Root->TryGetNumberField(TEXT("schemaVersion"), Version) || Version != 1
        || !Root->TryGetArrayField(TEXT("entries"), Entries))
        return Reject(TEXT("Visual import registry requires schemaVersion 1 and an entries array."));
    TMap<FName, FWarVisualImportBinding> Parsed;
    for (const TSharedPtr<FJsonValue>& Value : *Entries)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object)
            return Reject(TEXT("Visual import registry contains a malformed entry."));
        const TSharedPtr<FJsonObject> Entry = Value->AsObject();
        FString ProfileKey;
        FWarVisualImportBinding Binding;
        const TArray<TSharedPtr<FJsonValue>>* Animations = nullptr;
        if (!Entry->TryGetStringField(TEXT("profileKey"), ProfileKey) || ProfileKey.IsEmpty()
            || FName(*ProfileKey).IsNone() || Parsed.Contains(FName(*ProfileKey))
            || !Entry->TryGetStringField(TEXT("sourceModel"), Binding.SourceModel) || Binding.SourceModel.IsEmpty()
            || !Entry->TryGetStringField(TEXT("sourceSha256"), Binding.SourceSha256) || !WarValidation::IsSha256(Binding.SourceSha256)
            || !Entry->TryGetStringField(TEXT("skeletalMeshPath"), Binding.SkeletalMeshPath) || !ProjectObjectPath(Binding.SkeletalMeshPath)
            || !Entry->TryGetArrayField(TEXT("animationPaths"), Animations) || Animations->IsEmpty())
            return Reject(TEXT("Visual import registry identity, hash, mesh, or animations are invalid or duplicated."));
        for (const TSharedPtr<FJsonValue>& Animation : *Animations)
        {
            FString Path;
            if (!Animation.IsValid() || !Animation->TryGetString(Path) || !ProjectObjectPath(Path) || Binding.AnimationPaths.Contains(Path))
                return Reject(TEXT("Visual import registry requires distinct imported animation paths."));
            Binding.AnimationPaths.Add(Path);
        }
        Parsed.Add(FName(*ProfileKey), MoveTemp(Binding));
    }
    OutBindings = MoveTemp(Parsed);
    return true;
}

bool UWarContentSubsystem::ValidateVisualImportBinding(const UWarCharacterVisualDefinition* Visual,
    const TMap<FName, FWarVisualImportBinding>& Bindings, FString& OutError)
{
    const auto Reject = [&OutError](const TCHAR* Message) { OutError = Message; return false; };
    OutError.Reset();
    const FWarVisualImportBinding* Binding = Visual ? Bindings.Find(Visual->ProfileKey) : nullptr;
    if (!Binding) return Reject(TEXT("Character profile has no verified import binding. Import it before spawning."));
    if (!WarValidation::IsSha256(Visual->SourceSha256) || Visual->SourceModel != Binding->SourceModel
        || Visual->SourceSha256 != Binding->SourceSha256)
        return Reject(TEXT("Character source model/hash differs from its verified import binding."));
    if (Visual->SkeletalMesh.ToSoftObjectPath().ToString() != Binding->SkeletalMeshPath)
        return Reject(TEXT("Character skeletal mesh differs from its verified import binding."));
    if (Visual->AnimationBlueprint.IsNull() && Visual->IdleAnimation.IsNull())
        return Reject(TEXT("Character has no imported animation binding."));
    if ((!Visual->AnimationBlueprint.IsNull() && !Binding->AnimationPaths.Contains(Visual->AnimationBlueprint.ToSoftObjectPath().ToString()))
        || (!Visual->IdleAnimation.IsNull() && !Binding->AnimationPaths.Contains(Visual->IdleAnimation.ToSoftObjectPath().ToString())))
        return Reject(TEXT("Character animation differs from its verified import binding."));
    const USkeletalMesh* Mesh = Visual->SkeletalMesh.LoadSynchronous();
    if (!Mesh || Mesh->GetPathName() != Binding->SkeletalMeshPath)
        return Reject(TEXT("Verified skeletal mesh is missing or resolves to a different asset."));
    if (!Visual->IdleAnimation.IsNull())
    {
        const UAnimSequence* Idle = Visual->IdleAnimation.LoadSynchronous();
        if (!Idle || !Binding->AnimationPaths.Contains(Idle->GetPathName()))
            return Reject(TEXT("Verified idle sequence is missing or redirects to a different asset."));
    }
    if (!Visual->AnimationBlueprint.IsNull())
    {
        const UClass* AnimationClass = Visual->AnimationBlueprint.LoadSynchronous();
        if (!AnimationClass || !Binding->AnimationPaths.Contains(AnimationClass->GetPathName()))
            return Reject(TEXT("Verified animation class is missing or redirects to a different asset."));
    }
    return true;
}

bool UWarContentSubsystem::ValidatePlayableVisual(const UWarCharacterVisualDefinition* Visual, FString& OutError) const
{
    if (!VisualImportError.IsEmpty()) { OutError = VisualImportError; return false; }
    if (!ValidateVisualImportBinding(Visual, VisualImports, OutError)) return false;
    OutError = TEXT("Character visual identity does not match the exported playable profile.");
    const TSharedPtr<FJsonObject>* Careers = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Profiles = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Classes = nullptr;
    if (!Visual || !Manifest.IsValid() || !Manifest->TryGetObjectField(TEXT("careers"), Careers)
        || !(*Careers)->TryGetArrayField(TEXT("playableProfiles"), Profiles)
        || !(*Careers)->TryGetArrayField(TEXT("classes"), Classes)) return false;
    FString ExpectedClassName;
    const FString ExpectedRealm = Visual->Realm == EWarRealm::Aegis ? TEXT("aegis") : TEXT("riftbound");
    for (const TSharedPtr<FJsonValue>& Value : *Classes)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) continue;
        const TSharedPtr<FJsonObject> Class = Value->AsObject();
        FString Id, Name, Race, Realm;
        if (Class->TryGetStringField(TEXT("id"), Id) && Class->TryGetStringField(TEXT("name"), Name)
            && Class->TryGetStringField(TEXT("race"), Race) && Class->TryGetStringField(TEXT("realm"), Realm)
            && Id == Visual->ClassId.ToString() && Race == Visual->RaceId.ToString() && Realm == ExpectedRealm)
        { ExpectedClassName = Name; break; }
    }
    if (ExpectedClassName.IsEmpty()) return false;
    for (const TSharedPtr<FJsonValue>& Value : *Profiles)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) continue;
        const TSharedPtr<FJsonObject> Profile = Value->AsObject();
        FString Key, Race, ClassName, Body;
        if (Profile->TryGetStringField(TEXT("profileKey"), Key) && Profile->TryGetStringField(TEXT("race"), Race)
            && Profile->TryGetStringField(TEXT("className"), ClassName) && Profile->TryGetStringField(TEXT("bodyVariant"), Body)
            && Key == Visual->ProfileKey.ToString() && Race == Visual->RaceId.ToString()
            && ClassName == ExpectedClassName && Body == Visual->BodyVariant.ToString())
        { OutError.Reset(); return true; }
    }
    return false;
}
