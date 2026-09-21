#include "WarWorldEditCatalog.h"
#include "Misc/Paths.h"

TArray<FWarWorldEditCatalogEntry> WarWorldEditCatalog::Build(const TArray<FWarWorldEditObject>& Baseline)
{
    TMap<FString, FWarWorldEditCatalogEntry> Models;
    for (const auto& Row : Baseline)
    {
        if (!Row.TemplateId.IsNone() || Row.Id.IsNone() || Row.SourceIdentity.IsEmpty()) continue;
        auto* Existing = Models.Find(Row.SourceIdentity);
        // Pick a stable authored template regardless of actor enumeration order.
        if (Existing && !Row.Id.LexicalLess(Existing->TemplateId)) continue;
        FString MeshPath; Row.SourceIdentity.Split(TEXT(":"), &MeshPath, nullptr);
        if (MeshPath.IsEmpty()) continue;
        const FString Label = FPaths::GetBaseFilename(MeshPath).Replace(TEXT("aegis_house_"), TEXT("House "))
            .Replace(TEXT("aegis_rowhouse_"), TEXT("Rowhouse ")).Replace(TEXT("aegis_wall"), TEXT("Capital wall"))
            .Replace(TEXT("SM_MH_02_"), TEXT("Town kit ")).Replace(TEXT("_"), TEXT(" "));
        Models.Add(Row.SourceIdentity, { Row.Id, Label, Row.SourceIdentity });
    }
    TArray<FWarWorldEditCatalogEntry> Result; Models.GenerateValueArray(Result);
    Result.Sort([](const auto& A, const auto& B) {
        const int32 Order = A.Label.Compare(B.Label, ESearchCase::IgnoreCase);
        return Order == 0 ? A.TemplateId.LexicalLess(B.TemplateId) : Order < 0;
    });
    return Result;
}

TArray<FWarWorldEditCatalogEntry> WarWorldEditCatalog::Filter(const TArray<FWarWorldEditCatalogEntry>& Entries, const FString& Query)
{
    TArray<FString> Terms; Query.ParseIntoArrayWS(Terms);
    TArray<FWarWorldEditCatalogEntry> Result;
    for (const auto& Entry : Entries)
    {
        const FString Searchable = Entry.Label + TEXT(" ") + Entry.TemplateId.ToString();
        if (Terms.ContainsByPredicate([&Searchable](const FString& Term) { return !Searchable.Contains(Term, ESearchCase::IgnoreCase); })) continue;
        Result.Add(Entry);
    }
    return Result;
}
