#include "WarWorldVisualCatalog.h"
#include "WarTypes.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    bool AssetPath(const FString& Path)
    {
        const FSoftObjectPath Value(Path);
        return Value.IsValid() && Value.GetLongPackageName().StartsWith(TEXT("/Game/"))
            && !Value.GetAssetName().IsEmpty() && Value.GetSubPathString().IsEmpty()
            && !Path.Contains(TEXT("..")) && Path == Value.ToString();
    }
    bool Identity(const FString& Value)
    {
        if (Value.IsEmpty() || FName(*Value).IsNone()) return false;
        for (TCHAR Character : Value)
            if (!(Character >= 'a' && Character <= 'z') && !(Character >= '0' && Character <= '9') && Character != '_') return false;
        return true;
    }
}

FString WarWorldVisuals::Key(FName Purpose, FName Zone, FName Entity)
{ return Purpose.ToString() + TEXT(":") + Zone.ToString() + TEXT(":") + Entity.ToString(); }

bool WarWorldVisuals::Parse(const FString& Json, const FString& ContentSha256,
    TMap<FString, FWarWorldVisualBinding>& Bindings, FString& Error)
{
    Bindings.Reset(); Error.Reset();
    const auto Reject = [&Error]() { Error = TEXT("World visual catalog is missing, stale or malformed. Reconcile reviewed bindings before gathering."); return false; };
    TSharedPtr<FJsonObject> Root;
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    double Version = 0; FString Source; bool bProduction = true;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid()
        || !Root->TryGetNumberField(TEXT("schemaVersion"), Version) || Version != 1
        || !Root->TryGetStringField(TEXT("sourceContentSha256"), Source) || !WarValidation::IsSha256(Source) || Source != ContentSha256
        || !Root->TryGetBoolField(TEXT("productionAccepted"), bProduction) || bProduction
        || !Root->TryGetArrayField(TEXT("bindings"), Rows)) return Reject();
    TMap<FString, FWarWorldVisualBinding> Parsed;
    for (const auto& Value : *Rows)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return Reject();
        const auto Row = Value->AsObject();
        FWarWorldVisualBinding Binding;
        FString Zone, Entity, Visual, Purpose, Collision, Review;
        const TArray<TSharedPtr<FJsonValue>>* Materials = nullptr;
        if (!Row->TryGetStringField(TEXT("zone"), Zone) || !Identity(Zone)
            || !Row->TryGetStringField(TEXT("entity"), Entity) || !Identity(Entity)
            || !Row->TryGetStringField(TEXT("visualProp"), Visual) || !Identity(Visual)
            || !Row->TryGetStringField(TEXT("purpose"), Purpose)
                || (Purpose != TEXT("resource") && Purpose != TEXT("scenery") && Purpose != TEXT("training_dummy"))
            || !Row->TryGetStringField(TEXT("reviewState"), Review) || Review != TEXT("development")
            || !Row->TryGetStringField(TEXT("sourceModel"), Binding.SourceModel) || Binding.SourceModel.IsEmpty()
            || !Row->TryGetStringField(TEXT("sourceSha256"), Binding.SourceSha256) || !WarValidation::IsSha256(Binding.SourceSha256)
            || !Row->TryGetStringField(TEXT("mesh"), Binding.Mesh) || !AssetPath(Binding.Mesh)
            || !Row->TryGetStringField(TEXT("collision"), Collision) || Collision.IsEmpty()
            || !Row->TryGetArrayField(TEXT("materials"), Materials) || Materials->IsEmpty()) return Reject();
        for (const auto& Material : *Materials)
        {
            FString Path;
            if (!Material.IsValid() || !Material->TryGetString(Path) || !AssetPath(Path)) return Reject();
            Binding.Materials.Add(Path);
        }
        Binding.Zone = FName(*Zone); Binding.Entity = FName(*Entity); Binding.VisualProp = FName(*Visual);
        Binding.Purpose = FName(*Purpose); Binding.CollisionProfile = FName(*Collision);
        const FString Id = Key(Binding.Purpose, Binding.Zone, Binding.Entity);
        if (Parsed.Contains(Id)) return Reject();
        Parsed.Add(Id, MoveTemp(Binding));
    }
    Bindings = MoveTemp(Parsed);
    return true;
}

bool WarWorldVisuals::Matches(const FWarWorldVisualBinding& Binding, FName VisualProp,
    const FString& Mesh, const TArray<FString>& Materials, FName CollisionProfile)
{
    return !VisualProp.IsNone() && Binding.VisualProp == VisualProp && Binding.Mesh == Mesh
        && Binding.Materials == Materials && Binding.CollisionProfile == CollisionProfile;
}
