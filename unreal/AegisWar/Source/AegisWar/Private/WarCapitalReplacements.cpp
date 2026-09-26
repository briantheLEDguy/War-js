#include "WarCapitalReplacements.h"
#include "WarWorldEditHistory.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"

bool WarCapitalReplacements::RegisterReviewed(FWarWorldEditHistory& History,FString& Error)
{
    const FString Path=FPaths::ProjectContentDir()/TEXT("Migration/capital-expansion-replacements.json");
    if (!IFileManager::Get().FileExists(*Path)) return true;
    FString Json; TSharedPtr<FJsonObject> Root; const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if (IFileManager::Get().FileSize(*Path)>512000 || !FFileHelper::LoadFileToString(Json,*Path)
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root) || !Root.IsValid()
        || !Root->TryGetArrayField(TEXT("replacements"),Rows) || Rows->Num()>145)
    { Error=TEXT("Unreadable reviewed capital replacements."); return false; }
    for (const auto& Value:*Rows)
    {
        const TSharedPtr<FJsonObject>* Row=nullptr; const TArray<TSharedPtr<FJsonValue>>* Transform=nullptr;
        FString Id,PreviousSource,CurrentSource; bool Hidden=false;
        if (!Value->TryGetObject(Row) || !Row->IsValid() || !(*Row)->TryGetStringField(TEXT("id"),Id)
            || Id.IsEmpty() || Id.Len()>128 || !(*Row)->TryGetStringField(TEXT("previousSourceIdentity"),PreviousSource)
            || !(*Row)->TryGetStringField(TEXT("currentSourceIdentity"),CurrentSource)
            || !(*Row)->TryGetBoolField(TEXT("previousHidden"),Hidden)
            || !(*Row)->TryGetArrayField(TEXT("previousTransform"),Transform) || Transform->Num()!=10)
        { Error=TEXT("Invalid reviewed capital replacement record."); return false; }
        // Another capital may currently be unloaded. Admission is repeated when
        // a workbench is initialized with that city's actual trusted templates.
        if (!History.Find(FName(*Id))) continue;
        double N[10];
        for (int32 I=0; I<10; ++I)
            if (!(*Transform)[I]->TryGetNumber(N[I]) || !FMath::IsFinite(N[I]))
            { Error=TEXT("Invalid reviewed replacement transform."); return false; }
        const FWarWorldEditObject Previous{FName(*Id),FTransform(FQuat(N[3],N[4],N[5],N[6]),
            FVector(N[0],N[1],N[2]),FVector(N[7],N[8],N[9])),Hidden,PreviousSource};
        if (!History.AllowBaselineReplacement(Previous,CurrentSource,Error)) return false;
    }
    return true;
}
