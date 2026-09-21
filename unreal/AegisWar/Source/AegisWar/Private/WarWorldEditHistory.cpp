#include "WarWorldEditHistory.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    bool ValidTransform(const FTransform& Transform)
    {
        if (Transform.ContainsNaN() || !Transform.GetRotation().IsNormalized()
            || Transform.GetLocation().GetAbsMax() > 100000) return false;
        const FVector Scale = Transform.GetScale3D().GetAbs();
        return Scale.GetMin() >= 0.05 && Scale.GetMax() <= 20;
    }
    TArray<TSharedPtr<FJsonValue>> Rows(const TArray<FWarWorldEditObject>& Objects)
    {
        TArray<TSharedPtr<FJsonValue>> Result;
        for (const auto& Row : Objects)
        {
            const auto Object = MakeShared<FJsonObject>();
            Object->SetStringField(TEXT("id"), Row.Id.ToString());
            Object->SetBoolField(TEXT("hidden"), Row.bHidden);
            Object->SetStringField(TEXT("sourceIdentity"), Row.SourceIdentity);
            if (!Row.TemplateId.IsNone()) Object->SetStringField(TEXT("templateId"), Row.TemplateId.ToString());
            const FVector P = Row.Transform.GetLocation(), S = Row.Transform.GetScale3D();
            const FQuat Q = Row.Transform.GetRotation();
            TArray<TSharedPtr<FJsonValue>> Values;
            for (double Value : { P.X, P.Y, P.Z, Q.X, Q.Y, Q.Z, Q.W, S.X, S.Y, S.Z }) Values.Add(MakeShared<FJsonValueNumber>(Value));
            Object->SetArrayField(TEXT("transform"), Values);
            Result.Add(MakeShared<FJsonValueObject>(Object));
        }
        return Result;
    }
    FString BaselineText(const TArray<FWarWorldEditObject>& Objects)
    {
        const auto Root = MakeShared<FJsonObject>(); Root->SetArrayField(TEXT("objects"), Rows(Objects));
        FString Json; FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Json)); return Json;
    }
}

bool FWarWorldEditHistory::Initialize(const TArray<FWarWorldEditObject>& Objects, FString& Error)
{
    if (Objects.IsEmpty() || Objects.Num() > 10000) { Error = TEXT("Invalid world object count."); return false; }
    TSet<FName> Ids;
    for (const auto& Row : Objects)
    {
        if (Row.Id.IsNone() || Row.Id.ToString().Len() > 128 || Ids.Contains(Row.Id) || !ValidTransform(Row.Transform)
            || !Row.TemplateId.IsNone() || Row.SourceIdentity.Len() > 512)
        { Error = TEXT("Invalid or duplicate authored world object."); return false; }
        Ids.Add(Row.Id);
    }
    Baseline = Objects;
    Baseline.Sort([](const auto& A, const auto& B) { return A.Id.LexicalLess(B.Id); });
    Current = Baseline; Past.Reset(); Future.Reset(); Revision = 0; LoadedBaselineAdditions = 0; return true;
}

const FWarWorldEditObject* FWarWorldEditHistory::Find(const FName Id) const
{ return Current.FindByPredicate([Id](const auto& Row) { return Row.Id == Id; }); }

bool FWarWorldEditHistory::CheckRevision(const int32 Expected, FString& Error) const
{
    if (Current.IsEmpty() || Expected != Revision || Revision == MAX_int32)
    { Error = TEXT("World edits changed; refresh before editing."); return false; }
    return true;
}

bool FWarWorldEditHistory::Validate(const TArray<FWarWorldEditObject>& Objects, FString& Error) const
{
    if (Objects.Num() < Baseline.Num() || Objects.Num() > Baseline.Num() + 1000)
    { Error = TEXT("Draft object count exceeds the supported world limits."); return false; }
    TSet<FName> Ids;
    int32 BaselineCount = 0;
    for (const auto& Row : Objects)
    {
        const auto* Original = Baseline.FindByPredicate([&](const auto& Value) { return Value.Id == Row.Id; });
        if (Original)
        {
            if (!Row.TemplateId.IsNone()) { Error = TEXT("An authored object's model cannot be replaced by a draft."); return false; }
            ++BaselineCount;
        }
        else
        {
            FGuid CreatedId;
            const FString Id = Row.Id.ToString();
            if (!Id.StartsWith(TEXT("gm_")) || !FGuid::ParseExact(Id.RightChop(3), EGuidFormats::Digits, CreatedId))
            { Error = TEXT("Invalid created-object identity."); return false; }
            Original = Baseline.FindByPredicate([&](const auto& Value) { return Value.Id == Row.TemplateId; });
        }
        if (!Original || Ids.Contains(Row.Id) || !ValidTransform(Row.Transform) || Row.SourceIdentity != Original->SourceIdentity)
        { Error = TEXT("Invalid world object or transform."); return false; }
        if (const auto* Existing = Find(Row.Id); Existing && Existing->TemplateId != Row.TemplateId)
        { Error = TEXT("A live object's model template cannot be replaced by a draft."); return false; }
        const FVector Product = Original->Transform.GetScale3D() * Row.Transform.GetScale3D();
        if (Product.GetMin() <= 0) { Error = TEXT("Model coordinate handedness must be preserved."); return false; }
        Ids.Add(Row.Id);
    }
    if (BaselineCount != Baseline.Num()) { Error = TEXT("Draft omits authored world objects."); return false; }
    return true;
}

bool FWarWorldEditHistory::Create(const FName Id, const FName TemplateId, const FTransform& Transform,
    const int32 ExpectedRevision, FString& Error)
{
    if (!CheckRevision(ExpectedRevision, Error)) return false;
    const auto* Template = Baseline.FindByPredicate([TemplateId](const auto& Row) { return Row.Id == TemplateId; });
    if (!Template || Find(Id)) { Error = TEXT("Unknown model template or duplicate object identity."); return false; }
    auto Next = Current;
    Next.Add({ Id, Transform, false, Template->SourceIdentity, TemplateId });
    if (!Validate(Next, Error)) return false;
    Commit(MoveTemp(Next)); return true;
}

void FWarWorldEditHistory::Commit(TArray<FWarWorldEditObject> Objects)
{
    if (Past.Num() == 100) Past.RemoveAt(0);
    Past.Add(Current); Current = MoveTemp(Objects); Future.Reset(); ++Revision;
}

bool FWarWorldEditHistory::Edit(const FName Id, const FTransform& Transform, const bool bHidden,
    const int32 ExpectedRevision, FString& Error)
{
    if (!CheckRevision(ExpectedRevision, Error)) return false;
    auto Next = Current;
    auto* Row = Next.FindByPredicate([Id](const auto& Value) { return Value.Id == Id; });
    if (!Row) { Error = TEXT("Unknown world object."); return false; }
    if (Row->Transform.Equals(Transform, 0.0001) && Row->bHidden == bHidden)
    { Error = TEXT("No change to apply."); return false; }
    Row->Transform = Transform; Row->bHidden = bHidden;
    if (!Validate(Next, Error)) return false;
    Commit(MoveTemp(Next)); return true;
}

bool FWarWorldEditHistory::Undo(const bool bRedo, const int32 ExpectedRevision, FString& Error)
{
    if (!CheckRevision(ExpectedRevision, Error)) return false;
    auto& From = bRedo ? Future : Past; auto& To = bRedo ? Past : Future;
    if (From.IsEmpty()) { Error = bRedo ? TEXT("Nothing to redo.") : TEXT("Nothing to undo."); return false; }
    To.Add(Current); Current = From.Pop(); ++Revision; return true;
}

FString FWarWorldEditHistory::ExportDraft() const
{
    const auto Root = MakeShared<FJsonObject>();
    Root->SetNumberField(TEXT("schemaVersion"), 2); Root->SetStringField(TEXT("zoneId"), TEXT("aegis_capital"));
    Root->SetStringField(TEXT("baseline"), BaselineText(Baseline)); Root->SetArrayField(TEXT("objects"), Rows(Current));
    FString Json; FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Json)); return Json;
}

bool FWarWorldEditHistory::ImportDraft(const FString& Json, const int32 ExpectedRevision, FString& Error)
{
    if (!CheckRevision(ExpectedRevision, Error)) return false;
    TSharedPtr<FJsonObject> Root; double Version = 0; FString Zone, Base;
    const TArray<TSharedPtr<FJsonValue>>* Objects = nullptr;
    if (Json.Len() > 2000000 || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid()
        || !Root->TryGetNumberField(TEXT("schemaVersion"), Version) || (Version != 1 && Version != 2)
        || !Root->TryGetStringField(TEXT("zoneId"), Zone) || Zone != TEXT("aegis_capital")
        || !Root->TryGetStringField(TEXT("baseline"), Base)
        || !Root->TryGetArrayField(TEXT("objects"), Objects) || Objects->Num() > Baseline.Num() + 1000)
    { Error = TEXT("Draft is invalid or belongs to a different authored world revision."); return false; }
    // Allow additions to the imported city, but require every old authored
    // object to retain its exact original geometry fingerprint and placement.
    TSharedPtr<FJsonObject> SavedBase;
    const TArray<TSharedPtr<FJsonValue>>* SavedObjects = nullptr;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Base), SavedBase) || !SavedBase.IsValid()
        || !SavedBase->TryGetArrayField(TEXT("objects"), SavedObjects) || SavedObjects->IsEmpty()
        || SavedObjects->Num() > Baseline.Num() || Objects->Num() < SavedObjects->Num()
        || Objects->Num() > SavedObjects->Num() + 1000 || (Version == 1 && Objects->Num() != SavedObjects->Num()))
    { Error = TEXT("Draft has an invalid authored baseline."); return false; }
    TSet<FName> SavedIds;
    TArray<FWarWorldEditObject> ExpectedBase;
    for (const auto& Value : *SavedObjects)
    {
        const TSharedPtr<FJsonObject>* Object = nullptr; FString Id;
        if (!Value->TryGetObject(Object) || !Object->IsValid() || !(*Object)->TryGetStringField(TEXT("id"), Id)
            || Id.IsEmpty() || Id.Len() > 128 || SavedIds.Contains(FName(*Id)))
        { Error = TEXT("Draft has an invalid authored identity."); return false; }
        const auto* Original = Baseline.FindByPredicate([&](const auto& Row) { return Row.Id == FName(*Id); });
        if (!Original) { Error = FString::Printf(TEXT("Authored object %s was removed. Resolve the draft conflict before loading."), *Id); return false; }
        ExpectedBase.Add(*Original); SavedIds.Add(Original->Id);
    }
    ExpectedBase.Sort([](const auto& A, const auto& B) { return A.Id.LexicalLess(B.Id); });
    if (Base != BaselineText(ExpectedBase))
    { Error = TEXT("An existing authored object or model changed. Resolve the draft conflict before loading."); return false; }
    TArray<FWarWorldEditObject> Next;
    for (const auto& Value : *Objects)
    {
        const TSharedPtr<FJsonObject>* Object = nullptr;
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        FString Id, SourceIdentity, TemplateId; bool bHidden;
        if (!Value->TryGetObject(Object) || !Object->IsValid() || !(*Object)->TryGetStringField(TEXT("id"), Id)
            || Id.IsEmpty() || Id.Len() > 128 || !(*Object)->TryGetBoolField(TEXT("hidden"), bHidden)
            || !(*Object)->TryGetStringField(TEXT("sourceIdentity"), SourceIdentity) || SourceIdentity.Len() > 512
            || !(*Object)->TryGetArrayField(TEXT("transform"), Values) || Values->Num() != 10)
        { Error = TEXT("Invalid draft object."); return false; }
        if ((*Object)->HasField(TEXT("templateId")) && (Version != 2
            || !(*Object)->TryGetStringField(TEXT("templateId"), TemplateId) || TemplateId.IsEmpty() || TemplateId.Len() > 128))
        { Error = TEXT("Invalid model template in draft."); return false; }
        double Numbers[10];
        for (int32 I = 0; I < 10; ++I)
            if (!(*Values)[I]->TryGetNumber(Numbers[I]) || !FMath::IsFinite(Numbers[I]))
            { Error = TEXT("Invalid draft transform."); return false; }
        Next.Add({ FName(*Id), FTransform(FQuat(Numbers[3], Numbers[4], Numbers[5], Numbers[6]),
            FVector(Numbers[0], Numbers[1], Numbers[2]), FVector(Numbers[7], Numbers[8], Numbers[9])), bHidden, SourceIdentity, FName(*TemplateId) });
        if (TemplateId.IsEmpty() && !SavedIds.Contains(FName(*Id)))
        { Error = TEXT("Draft edits an authored object outside its original baseline."); return false; }
        if (!TemplateId.IsEmpty() && !SavedIds.Contains(FName(*TemplateId)))
        { Error = TEXT("Draft uses a model template outside its original baseline."); return false; }
    }
    for (const auto& Original : Baseline) if (!SavedIds.Contains(Original.Id)) Next.Add(Original);
    if (!Validate(Next, Error)) return false;
    Next.Sort([](const auto& A, const auto& B) { return A.Id.LexicalLess(B.Id); });
    Commit(MoveTemp(Next)); LoadedBaselineAdditions = Baseline.Num() - SavedIds.Num(); return true;
}
